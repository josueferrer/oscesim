import streamlit as st, time, json, os, random
from case_generator import generate_station, custom_case_generator
from evaluator import evaluate, render_mark_sheet
from timer_utils import start_timer, remaining
from hint_engine import generate_hint
from openai_utils import chat, patient_simulation
from categories import CATEGORIES
from prompt_templates import CANDIDATE_INSTRUCTIONS
from checklist import CHECKLIST, MAX_SCORE

# Setup page config
st.set_page_config("OSCE Chat Simulator", layout="wide", page_icon="🩺")

# Initialize session state
if "phase" not in st.session_state:
    st.session_state.phase = "setup"

# Make sure API key is properly set up
def get_api_key():
    """Get API key from environment or secrets"""
    # First try to get from environment
    api_key = os.getenv("OPENAI_API_KEY")
    
    # If not in environment, try to get from Streamlit secrets
    if not api_key and hasattr(st, "secrets") and "openai" in st.secrets:
        api_key = st.secrets["openai"]["api_key"]
        
    return api_key

# OSCE marking criteria constants
HISTORY_CRITERIA = [
    "Greets patient / introduces self and establishes rapport",
    "Clarifies details of chief complaint",
    "Asks about associated symptoms",
    "Rules out red flags",
    "Rules out B-symptom red flags",
    "Performs review of systems",
    "Takes OB/GYN history (if applicable)",
    "Asks about past medical history",
    "Asks about past surgical history",
    "Asks about drug and allergy history",
    "Asks about family history",
    "Takes social history",
    "Takes neonatal history (if applicable)",
    "Asks about developmental milestones (if applicable)",
    "Elicits Ideas, Concerns, Expectations, and Effects on life",
    "Screens using PHQ2",
    "Screens for vaccination and preventive health"
]

EXAMINATION_CRITERIA = [
    "Takes permission, washes hands, maintains privacy",
    "Measures vital signs",
    "Assesses general appearance",
    "Examines main system involved",
    "Examines related systems",
    "Elicits specific signs to confirm diagnosis",
    "Performs focused examinations"
]

LAB_CRITERIA = [
    "Orders appropriate lab investigations",
    "Interprets radiological findings"
]

MANAGEMENT_CRITERIA = [
    "Clarifies diagnosis and explains management options",
    "Reassures with empathy and honesty",
    "Provides non-pharmacological advice",
    "Prescribes pharmacological treatment",
    "Refers to appropriate services",
    "Orders further investigations",
    "Advises on follow-up/observation",
    "Discusses prevention and health promotion"
]

COMMUNICATION_CRITERIA = [
    "Demonstrates effective communication, active listening, and empathy"
]

### ------------------ 1. SETUP SCREEN ------------------ ###
if st.session_state.phase == "setup":
    st.title("🩺 OSCE Chat Simulator")
    
    # Show API key warning if missing
    api_key = get_api_key()
    if not api_key:
        st.error("⚠️ No OpenAI API key found. Please set the OPENAI_API_KEY environment variable or in Streamlit secrets.")
        st.stop()
    
    # Two-column layout for setup
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("Exam Settings")
        lang = st.selectbox("Language", {"en": "English", "ar": "Arabic"})
        exam_mode = st.radio("Exam Mode", ["Random Cases", "Custom Cases", "Upload JSON Case"])
        
        if exam_mode == "Random Cases":
            # Add specialty selection
            specialty = st.selectbox("Medical Specialty", list(CATEGORIES.keys()))
            chief_options = CATEGORIES[specialty]
            
            # Allow user to select specific chief complaints or random
            chief_selection = st.radio("Chief Complaint Selection", ["Random", "Choose Specific"])
            if chief_selection == "Choose Specific":
                selected_chief = st.selectbox("Chief Complaint", chief_options)
            
            # Number of stations and time settings
            n_stn = st.number_input("Number of stations", 1, 10, 3)
            t_min = st.slider("Minutes per station", 3, 10, 5)
            
        elif exam_mode == "Custom Cases":
            n_stn = st.number_input("Number of stations", 1, 5, 1)
            t_min = st.slider("Minutes per station", 3, 15, 8)
            
            st.subheader("Custom Case Description")
            custom_case_desc = st.text_area(
                "Describe the case(s) you want to practice",
                placeholder="E.g., A 65-year-old male with chest pain and history of hypertension...",
                height=150
            )
        else:  # Upload JSON Case
            t_min = st.slider("Minutes per station", 3, 15, 8)
            
            st.subheader("Upload Case File")
            uploaded_file = st.file_uploader("Upload JSON case file", type="json")
            if uploaded_file:
                try:
                    st.success("✅ Case file uploaded successfully!")
                except:
                    st.error("❌ Invalid JSON file. Please check the format and try again.")
    
    with col2:
        st.subheader("OSCE Simulation Features")
        st.markdown("""
        - ⏱️ Timed stations with countdown timer
        - 👨‍⚕️ AI-powered patient simulation
        - 💊 Clinical cases with detailed parameters
        - 💡 Hints available for guidance
        - 📝 Mandatory final diagnosis entry
        - 📊 Detailed performance feedback
        """)
        
        st.info("During the exam, take a complete history, perform appropriate examinations, and formulate a diagnosis.")
    
    if st.button("Start Exam", type="primary"):
        st.session_state.lang = lang
        st.session_state.duration = 60 * t_min  # Store duration in seconds
        
        # Generate stations based on user's choice
        with st.spinner("Generating exam cases... This may take a moment"):
            if exam_mode == "Random Cases":
                # Generate unique cases for each station
                st.session_state.stations = []
                for i in range(n_stn):
                    # Use selected chief complaint if specified
                    if chief_selection == "Choose Specific":
                        custom_case = {"chief_complaint": selected_chief}
                        new_case = generate_station(lang, custom_case)
                    else:
                        # Use a random chief complaint from the selected specialty
                        chief = random.choice(chief_options)
                        custom_case = {"chief_complaint": chief}
                        new_case = generate_station(lang, custom_case)
                    
                    # Initialize runtime state for this station
                    new_case["_runtime"] = {
                        "timer_started": False,
                        "diagnosis_popup": False,
                        "diagnosis_submitted": False,
                        "lab_results_viewed": False
                    }
                    
                    st.session_state.stations.append(new_case)
                    
            elif exam_mode == "Custom Cases":
                if not custom_case_desc.strip():
                    st.error("Please provide a description for your custom case")
                    st.stop()
                
                case = custom_case_generator(lang, custom_case_desc)
                case["_runtime"] = {
                    "timer_started": False,
                    "diagnosis_popup": False,
                    "diagnosis_submitted": False,
                    "lab_results_viewed": False
                }
                st.session_state.stations = [case]
                
            else:  # Upload JSON Case
                if not uploaded_file:
                    st.error("Please upload a case file")
                    st.stop()
                    
                try:
                    case = json.load(uploaded_file)
                    case["_runtime"] = {
                        "timer_started": False,
                        "diagnosis_popup": False,
                        "diagnosis_submitted": False,
                        "lab_results_viewed": False
                    }
                    st.session_state.stations = [case]
                except Exception as e:
                    st.error(f"Error loading case file: {str(e)}")
                    st.stop()
        
        st.session_state.current = 0
        st.session_state.phase = "exam"
        st.rerun()

### ------------------ 2. EXAM LOOP ------------------ ###
elif st.session_state.phase == "exam":
    s_idx = st.session_state.current
    station = st.session_state.stations[s_idx]
    runtime = station["_runtime"]

    # Setup per-station session vars
    if not runtime["timer_started"]:
        duration = st.session_state.get("duration", 60*5)  # Default to 5 minutes if not set
        runtime["timer"] = start_timer(duration)
        runtime["timer_started"] = True
        # Initialize message history for this station
        runtime["msgs"] = []
    
    # Get session data
    if runtime.get("timer") is None:
        runtime["timer"] = start_timer(st.session_state.get("duration", 300))  # Default to 5 mins if no duration set
    secs = remaining(runtime.get("timer"))
    
    # Candidate instructions
    with st.expander("📝 Candidate Instructions", expanded=True):
        st.markdown(CANDIDATE_INSTRUCTIONS.format(
            minutes=st.session_state.duration//60,
            name=station["patientInfo"]["name"],
            age=station["patientInfo"]["age"],
            gender=station["patientInfo"]["gender"],
            chief=station["chiefComplaint"]
        ))
    
    # Page layout: sidebar + main content
    # Sidebar for patient info and tools
    with st.sidebar:
        st.subheader("📋 Tools")
        
        # Hint button
        if st.button("💡 Hint"):
            transcript = "\n".join(m["content"] for m in runtime["msgs"] if m["role"] == "user")
            hint = generate_hint(st.session_state.lang, transcript)
            st.info(f"**Hint:** {hint}")
        
        # Show Case Details (collapse by default)
        with st.expander("📑 Patient Basic Info", expanded=False):
            patient_info = station.get("patientInfo", {})
            st.write(f"**Name:** {patient_info.get('name', 'Unknown')}")
            st.write(f"**Age:** {patient_info.get('age', 'Unknown')}")
            st.write(f"**Gender:** {patient_info.get('gender', 'Unknown')}")
            st.write(f"**Occupation:** {patient_info.get('occupation', 'Unknown')}")
            
        # Lab/Imaging Results (if available and if user clicks to view)
        if not runtime.get("lab_results_viewed", False):
            if st.button("🧪 Request Lab Results"):
                runtime["lab_results_viewed"] = True
            
        if runtime.get("lab_results_viewed", False):
            with st.expander("Lab Results", expanded=True):
                lab_results = station.get("labResults", {})
                if lab_results:
                    for test, result in lab_results.items():
                        st.write(f"**{test}:** {result}")
                else:
                    st.write("No lab results available for this case.")
                    
        # Timer display in sidebar too for visibility
        st.metric("⏰ Time remaining", f"{secs//60}:{secs%60:02d}")
        
    # Main content area
    st.header(f"Station {s_idx+1}")
    
    # Progress indicator
    progress_text = f"Station {s_idx+1}/{len(st.session_state.stations)}"
    st.progress(s_idx / len(st.session_state.stations))
    
    # Chief complaint as initial context
    chief_complaint = station.get("chiefComplaint", "")
    st.info(f"**Chief complaint:** {chief_complaint}")

    # Chat interface with patient
    st.subheader("Patient Consultation")
    
    # Chat container
    chat_container = st.container()
    
    # Initialize messages if needed
    if "msgs" not in runtime or not runtime["msgs"]:
        # Add initial patient greeting
        patient_info = station.get("patientInfo", {})
        patient_name = patient_info.get("name", "Patient")
        initial_msg = {
            "role": "assistant", 
            "content": f"Hello doctor. I'm {patient_name}. I'm here because of {chief_complaint}."
        }
        runtime["msgs"] = [initial_msg]
    
    # Display chat history
    with chat_container:
        for m in runtime["msgs"]:
            if m["role"] == "user":
                st.chat_message("user").write(m["content"])
            elif m["role"] == "assistant":
                st.chat_message("assistant").write(m["content"])
    
    # Chat input
    prompt = st.chat_input("Ask the patient...", disabled=secs==0)
    if prompt:
        # Add user message to history
        runtime["msgs"].append({"role": "user", "content": prompt})
        
        # Get AI response using patient simulation
        chat_history = [
            {"role": m["role"], "content": m["content"]} 
            for m in runtime["msgs"][:-1]  # Exclude the just-added message
        ]
        
        # Extract patient details for better simulation
        patient_info = station.get("patientInfo", {})
        history_details = station.get("historyDetails", {})
        past_medical_history = station.get("pastMedicalHistory", [])
        medications = station.get("medications", [])
        social_history = station.get("socialHistory", {})
        
        reply = patient_simulation(
            patient_case=station,
            user_message=prompt,
            chat_history=chat_history,
            model="gpt-4o"
        )
        
        # Add AI response to history
        runtime["msgs"].append({"role": "assistant", "content": reply})
        st.rerun()

    ### ---- Diagnosis input unlocks near end of time ----
    # Get remaining seconds again in case of changes
    remaining_secs = secs if isinstance(secs, int) else 0
    
    # Show diagnosis popup in the last 90 seconds or when time is up
    if remaining_secs <= 90 and not runtime.get("diagnosis_popup", False):
        runtime["diagnosis_popup"] = True

    # Diagnosis popup
    if runtime.get("diagnosis_popup", False) and not runtime.get("diagnosis_submitted", False):
        # Use st.container to create a persistent popup-like area
        diagnosis_popup = st.container()
        
        with diagnosis_popup:
            st.warning("⚠️ Time is almost up! Please provide your diagnosis.")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if "dx" not in runtime:
                    runtime["dx"] = ""
                    
                runtime["dx"] = st.text_input(
                    "Final Diagnosis",
                    value=runtime.get("dx", ""),
                    placeholder="Enter your diagnosis here..."
                )
                
                runtime["ddx"] = st.text_area(
                    "Differential Diagnoses (optional)",
                    value=runtime.get("ddx", ""),
                    placeholder="List other possible diagnoses"
                )
                
            with col2:
                submit_dx = st.button("Submit Diagnosis")
                if submit_dx and runtime["dx"]:
                    runtime["diagnosis_submitted"] = True
                    if secs == 0:
                        # Function to handle moving to next station
                        transcript = "\n".join(m["content"] for m in runtime["msgs"] if m["role"] == "user")
                        result = evaluate(
                            st.session_state.lang, 
                            transcript,
                            runtime.get("dx", ""), 
                            station["answer_key"],
                            station
                        )
                        station["result"] = result
                        station["transcript"] = transcript
                        station["student_dx"] = runtime.get("dx", "")
                        
                        # Prepare for next station
                        st.session_state.current += 1
                        
                        # If all stations complete, move to results phase
                        if st.session_state.current >= len(st.session_state.stations):
                            st.session_state.phase = "results"
                    st.rerun()

    # Auto-submit when timer hits zero
    if secs == 0:
        # If diagnosis not submitted yet, force the diagnosis popup
        if not runtime.get("diagnosis_submitted", False):
            runtime["diagnosis_popup"] = True
            st.error("⚠️ Time's up! You must submit a diagnosis to continue.")
        else:
            # Function to handle moving to next station
            transcript = "\n".join(m["content"] for m in runtime["msgs"] if m["role"] == "user")
            result = evaluate(
                st.session_state.lang, 
                transcript,
                runtime.get("dx", ""), 
                station["answer_key"],
                station
            )
            station["result"] = result
            station["transcript"] = transcript
            station["student_dx"] = runtime.get("dx", "")
            
            # Prepare for next station
            st.session_state.current += 1
            
            # If all stations complete, move to results phase
            if st.session_state.current >= len(st.session_state.stations):
                st.session_state.phase = "results"
            
            st.rerun()

### ------------------ 3. RESULTS DASHBOARD ------------------ ###
else:
    st.title("📊 OSCE Examination Results")
    
    # Calculate overall score
    total_score = 0
    max_score = 0
    
    for i, s in enumerate(st.session_state.stations):
        if "result" in s:
            total_score += s["result"]["overall_pct"]
            max_score += 100
    
    overall_percent = round(total_score / max_score * 100, 1) if max_score > 0 else 0
    
    # Display overall score with color coding
    if overall_percent >= 70:
        st.success(f"### Overall Score: {overall_percent}% - PASS")
    elif overall_percent >= 60:
        st.warning(f"### Overall Score: {overall_percent}% - BORDERLINE PASS")
    else:
        st.error(f"### Overall Score: {overall_percent}% - FAIL")
    
    # Display individual station results
    st.subheader("Station Details")
    
    # Create two tabs - one for performance summary and one for case details
    tab1, tab2, tab3 = st.tabs(["📊 Performance Summary", "📋 Examiner Mark Sheets", "🔍 Full Case Details"])
    
    with tab1:
        for i, s in enumerate(st.session_state.stations):
            if "result" not in s:
                continue
                
            res = s["result"]
            expected_dx = s["answer_key"]["main_diagnosis"]
            student_dx = s.get("student_dx", "")
            
            # Create an expandable section for each station
            with st.expander(f"Station {i+1}: {s['chiefComplaint']} - Score: {res['overall_pct']}%", expanded=i==0):
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.markdown("#### Diagnostic Assessment")
                    st.write(f"**Your diagnosis:** {student_dx}")
                    st.write(f"**Correct diagnosis:** {expected_dx}")
                    
                    # Score breakdown
                    st.markdown("#### Score Breakdown")
                    st.write(f"**History taking:** {res.get('history_pct', res.get('checklist_pct', 0))}%")
                    st.write(f"**Examination:** {res.get('exam_pct', 'N/A')}%")
                    st.write(f"**Lab & Radiology:** {res.get('lab_pct', 'N/A')}%")
                    st.write(f"**Management:** {res.get('management_pct', 'N/A')}%")
                    st.write(f"**Interaction:** {res.get('interaction_pct', 'N/A')}%")
                    st.write(f"**Diagnosis accuracy:** {res['diagnosis_pct']}%")
                    
                    # Key missed items
                    st.markdown("#### Areas for Improvement")
                    missed = res["missed_items"]
                    if missed:
                        for item in missed:
                            st.write(f"- {item}")
                    else:
                        st.write("Great job! No major items missed.")
                
                with col2:
                    # Patient details
                    st.markdown("#### Patient Information")
                    
                    patient_info = s.get("patientInfo", {})
                    if patient_info:
                        st.write(f"**Name:** {patient_info.get('name', 'Unknown')}")
                        st.write(f"**Age:** {patient_info.get('age', 'Unknown')}")
                        st.write(f"**Gender:** {patient_info.get('gender', 'Unknown')}")
                    
                    # Management recommendations
                    st.markdown("#### Recommended Management")
                    management_steps = s["answer_key"].get("management", [])
                    if management_steps:
                        for step in management_steps:
                            st.write(f"- {step}")
                    else:
                        st.write("No specific management provided for this case.")
    
    with tab2:
        for i, s in enumerate(st.session_state.stations):
            if "result" not in s:
                continue
            
            # Create an expandable section for each station
            with st.expander(f"Station {i+1}: {s['chiefComplaint']}", expanded=i==0):
                res = s["result"]
                raw_scores = res.get("raw_scores", {})
                student_dx = s.get("student_dx", "")
                correct_dx = s["answer_key"]["main_diagnosis"]
                dx_score = res["diagnosis_pct"]
                total_score = res["overall_pct"]
                comments = res.get("comments", "")
                
                # Render mark sheet
                mark_sheet = render_mark_sheet(
                    raw_scores, 
                    student_dx, 
                    correct_dx, 
                    dx_score, 
                    total_score, 
                    comments
                )
                
                st.markdown(mark_sheet)
                
                # Add download button for the mark sheet
                mark_sheet_pdf = f"osce_mark_sheet_station_{i+1}.pdf"
                st.download_button(
                    "Download Mark Sheet",
                    mark_sheet,
                    file_name=f"osce_mark_sheet_station_{i+1}.md",
                    mime="text/markdown"
                )
    
    with tab3:
        for i, s in enumerate(st.session_state.stations):
            if "result" not in s:
                continue
            
            # Create an expandable section for each station
            with st.expander(f"Station {i+1}: {s['chiefComplaint']}", expanded=i==0):
                # Remove system/internal data for cleaner display
                display_data = {k: v for k, v in s.items() if k not in ['result', 'transcript', 'student_dx', 'generated_timestamp', '_runtime']}
                st.json(display_data)
    
    # Final recommendations
    st.subheader("Examiner's Recommendations")
    
    # Generate personalized feedback based on results
    overall_feedback = ""
    if overall_percent >= 80:
        overall_feedback = "Excellent performance overall. You demonstrated strong clinical reasoning and patient communication skills."
    elif overall_percent >= 70:
        overall_feedback = "Good performance. You covered most essential elements but could improve in some specific areas."
    elif overall_percent >= 60:
        overall_feedback = "Adequate performance, but there are several important areas that need improvement."
    else:
        overall_feedback = "Your performance needs significant improvement. Focus on the core elements of history taking, examination techniques, and diagnostic reasoning."
    
    st.write(overall_feedback)
    
    # Restart button
    if st.button("Start New Exam", type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.phase = "setup"
        st.rerun() 