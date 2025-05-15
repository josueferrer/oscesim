import streamlit as st, time
from case_generator import generate_station
from evaluator import evaluate
from timer_utils import start_timer, remaining
from hint_engine import generate_hint
from openai_utils import chat

st.set_page_config("OSCE Chat Simulator", layout="wide")
if "phase" not in st.session_state:
    st.session_state.phase="setup"

### ------------------ 1. SETUP SCREEN ------------------ ###
if st.session_state.phase=="setup":
    st.title("🩺 OSCE Chat Simulator")
    lang = st.selectbox("Language",{"en":"English","ar":"Arabic"})
    n_stn = st.number_input("Number of stations",1,10,3)
    t_min = st.slider("Minutes per station",3,10,5)
    if st.button("Start Exam"):
        st.session_state.lang=lang
        st.session_state.duration = 60 * t_min  # Store the duration in session state
        st.session_state.stations=[generate_station(lang) for _ in range(n_stn)]
        st.session_state.current=0
        st.session_state.phase="exam"
        st.experimental_rerun()

### ------------------ 2. EXAM LOOP ------------------ ###
elif st.session_state.phase=="exam":
    s_idx = st.session_state.current
    station = st.session_state.stations[s_idx]

    # per‑station session vars
    if "timer" not in st.session_state:
        duration = st.session_state.get("duration", 60*5)  # Default to 5 minutes if not set
        st.session_state.timer = start_timer(duration)

    # Header + timer
    col1,col2 = st.columns([3,1])
    col1.subheader(f"Station {s_idx+1}")
    secs = remaining(st.session_state.timer)
    col2.metric("⏰ Time left",f"{secs//60}:{secs%60:02d}")

    # Chat memory container
    if "msgs" not in st.session_state: 
        st.session_state.msgs = [
          {"role":"system","content":"You are the patient. Answer brief, realistic."},
          {"role":"assistant","content":station["chiefComplaint"]}
        ]
    # Display prior chat
    for m in st.session_state.msgs[1:]:
        st.chat_message(m["role"]).write(m["content"])

    ### ---- Student input ----
    prompt = st.chat_input("Ask / respond…", disabled=secs==0)
    if prompt:
        st.session_state.msgs.append({"role":"user","content":prompt})
        # Using GPT-4.1 for patient simulation - lower temperature for consistent patient responses
        reply = chat(st.session_state.msgs, model="gpt-4.1", temperature=0.3, max_tokens=120)
        st.session_state.msgs.append({"role":"assistant","content":reply})
        st.experimental_rerun()

    ### ---- Hint button ----
    with st.sidebar:
        if st.button("💡 Hint"):
            hint = generate_hint(st.session_state.lang,
                        "\n".join(m["content"] for m in st.session_state.msgs if m["role"]=="user"))
            st.info(hint)

    ### ---- Diagnosis input unlocks at last 60s ----
    if secs <= 60 and "dx" not in st.session_state:
        st.session_state.dx = st.text_input("📝 Final Diagnosis (submit before time ends)")

    ### ---- Auto‑submit when timer hits zero ----
    if secs == 0:
        transcript = "\n".join(m["content"] for m in st.session_state.msgs if m["role"]=="user")
        result = evaluate(st.session_state.lang, transcript,
                          st.session_state.get("dx",""), station["answer_key"])
        st.session_state.stations[s_idx]["result"]=result
        # prepare next
        st.session_state.current += 1
        st.session_state.msgs, st.session_state.timer, st.session_state.dx = [], None, None
        if st.session_state.current >= len(st.session_state.stations):
            st.session_state.phase="results"
        st.experimental_rerun()

### ------------------ 3. RESULTS DASHBOARD ------------------ ###
else:
    st.title("📊 Exam Results")
    for i, s in enumerate(st.session_state.stations):
        res=s["result"]; exp=s["answer_key"]["main_diagnosis"]
        st.subheader(f"Station {i+1} — {res['overall_pct']} %")
        st.write(f"Checklist: {res['checklist_pct']} % | Diagnosis: {res['diagnosis_pct']} %")
        st.write(f"Your Dx: {st.session_state.stations[i].get('student_dx','')} | Correct: **{exp}**")
        with st.expander("Missed checklist items"):
            st.write(res["missed_items"])
        with st.expander("Full hidden case"):
            st.json(s) 