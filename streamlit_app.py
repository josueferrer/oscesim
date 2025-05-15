import streamlit as st, time
from case_generator import generate_station, custom_case_generator
from evaluator import evaluate
from timer_utils import start_timer, remaining
from hint_engine import generate_hint
from openai_utils import chat, patient_simulation

st.set_page_config("OSCE Chat Simulator", layout="wide", page_icon="🩺")
if "phase" not in st.session_state:
    st.session_state.phase = "setup"

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
    
    # Two-column layout for setup
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("Exam Settings")
        lang = st.selectbox("Language", {"en": "English", "ar": "Arabic"})
        exam_mode = st.radio("Exam Mode", ["Random Cases", "Custom Cases"])
        
        if exam_mode == "Random Cases":
            n_stn = st.number_input("Number of stations", 1, 10, 3)
            t_min = st.slider("Minutes per station", 3, 10, 5)
        else:
            n_stn = st.number_input("Number of stations", 1, 5, 1)
            t_min = st.slider("Minutes per station", 3, 15, 8)
            
            st.subheader("Custom Case Description")
            custom_case_desc = st.text_area(
                "Describe the case(s) you want to practice",
                placeholder="E.g., A 65-year-old male with chest pain and history of hypertension...",
                height=150
            )
    
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
        if exam_mode == "Random Cases":
            st.session_state.stations = [generate_station(lang) for _ in range(n_stn)]
        else:
            if not custom_case_desc.strip():
                st.error("Please provide a description for your custom case")
                st.stop()
            
            with st.spinner("Generating custom case..."):
                st.session_state.stations = [custom_case_generator(lang, custom_case_desc)]
        
        st.session_state.current = 0
        st.session_state.phase = "exam"
        st.rerun()

### ------------------ 2. EXAM LOOP ------------------ ###
elif st.session_state.phase == "exam":
    s_idx = st.session_state.current
    station = st.session_state.stations[s_idx]

    # Setup per-station session vars
    if "timer" not in st.session_state:
        duration = st.session_state.get("duration", 60*5)  # Default to 5 minutes if not set
        st.session_state.timer = start_timer(duration)
        # Initialize message history for this station
        st.session_state.msgs = []

    # Get session data
    if st.session_state.timer is None:
        st.session_state.timer = start_timer(st.session_state.get("duration", 60*5))
    secs = remaining(st.session_state.timer)
    
    # Page layout: sidebar + main content
    # Sidebar for patient info and tools
    with st.sidebar:
        st.subheader("📋 Tools")
        
        # Hint button
        if st.button("💡 Hint"):
            transcript = "\n".join(m["content"] for m in st.session_state.msgs if m["role"] == "user")
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
        if "lab_results_viewed" not in st.session_state:
            st.session_state.lab_results_viewed = False
            
        if st.button("🧪 Request Lab Results"):
            st.session_state.lab_results_viewed = True
            
        if st.session_state.lab_results_viewed:
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
    if "msgs" not in st.session_state or not st.session_state.msgs:
        # Add system message for context (not shown to user)
        st.session_state.msgs = []
        
        # Add initial patient greeting
        initial_msg = {
            "role": "assistant", 
            "content": f"Hello doctor. I'm here because of {chief_complaint}."
        }
        st.session_state.msgs.append(initial_msg)
    
    # Display chat history
    with chat_container:
        for m in st.session_state.msgs:
            if m["role"] == "user":
                st.chat_message("user").write(m["content"])
            elif m["role"] == "assistant":
                st.chat_message("assistant").write(m["content"])
    
    # Chat input
    prompt = st.chat_input("Ask the patient...", disabled=secs==0)
    if prompt:
        # Add user message to history
        st.session_state.msgs.append({"role": "user", "content": prompt})
        
        # Get AI response using patient simulation
        chat_history = [
            {"role": m["role"], "content": m["content"]} 
            for m in st.session_state.msgs[:-1]  # Exclude the just-added message
        ]
        
        reply = patient_simulation(
            patient_case=station,
            user_message=prompt,
            chat_history=chat_history,
            model="gpt-4o"
        )
        
        # Add AI response to history
        st.session_state.msgs.append({"role": "assistant", "content": reply})
        st.rerun()

    ### ---- Diagnosis input unlocks near end of time ----
    remaining_secs = secs
    if remaining_secs <= 90 and "diagnosis_popup" not in st.session_state:
        st.session_state.diagnosis_popup = True

    # Diagnosis popup
    if "diagnosis_popup" in st.session_state and st.session_state.diagnosis_popup:
        # Use st.container to create a persistent popup-like area
        diagnosis_popup = st.container()
        
        with diagnosis_popup:
            st.warning("⚠️ Time is almost up! Please provide your diagnosis.")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if "dx" not in st.session_state:
                    st.session_state.dx = ""
                    
                st.session_state.dx = st.text_input(
                    "Final Diagnosis",
                    value=st.session_state.dx,
                    placeholder="Enter your diagnosis here..."
                )
                
                st.session_state.ddx = st.text_area(
                    "Differential Diagnoses (optional)",
                    placeholder="List other possible diagnoses"
                )
                
            with col2:
                submit_dx = st.button("Submit Diagnosis")
                if submit_dx and st.session_state.dx:
                    st.session_state.diagnosis_submitted = True
                    st.session_state.diagnosis_popup = False
                    if secs == 0:
                        # Force proceed to next station
                        proceed_to_next_station()
                    st.rerun()

    # Auto-submit when timer hits zero
    if secs == 0:
        # Function to handle moving to next station
        def proceed_to_next_station():
            transcript = "\n".join(m["content"] for m in st.session_state.msgs if m["role"] == "user")
            result = evaluate(
                st.session_state.lang, 
                transcript,
                st.session_state.get("dx", ""), 
                station["answer_key"]
            )
            st.session_state.stations[s_idx]["result"] = result
            st.session_state.stations[s_idx]["transcript"] = transcript
            st.session_state.stations[s_idx]["student_dx"] = st.session_state.get("dx", "")
            
            # Prepare for next station
            st.session_state.current += 1
            st.session_state.msgs = []
            st.session_state.timer = None
            st.session_state.dx = None
            
            if "diagnosis_popup" in st.session_state:
                del st.session_state.diagnosis_popup
                
            if "diagnosis_submitted" in st.session_state:
                del st.session_state.diagnosis_submitted
                
            if "lab_results_viewed" in st.session_state:
                del st.session_state.lab_results_viewed
                
            # If all stations complete, move to results phase
            if st.session_state.current >= len(st.session_state.stations):
                st.session_state.phase = "results"
                
            st.rerun()
        
        # If diagnosis not submitted yet, force the diagnosis popup
        if "diagnosis_submitted" not in st.session_state:
            st.session_state.diagnosis_popup = True
            st.error("⚠️ Time's up! You must submit a diagnosis to continue.")
        else:
            proceed_to_next_station()

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
                st.write(f"**Management:** {res.get('management_pct', 'N/A')}%")
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
                    
            # Full case details at the bottom of each expander
            with st.expander("Full Case Details", expanded=False):
                # Remove system/internal data for cleaner display
                display_data = {k: v for k, v in s.items() if k not in ['result', 'transcript', 'student_dx', 'generated_timestamp']}
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