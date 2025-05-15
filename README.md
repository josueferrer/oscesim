# OSCE Chat Simulator – Streamlit

### Local run
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
streamlit run streamlit_app.py
```

## Deploy to Streamlit Cloud
1. Push repo to GitHub.
2. In Streamlit Cloud ➜ New app ➜ pick streamlit_app.py.
3. Secrets tab → add OPENAI_API_KEY.
4. Click Deploy (cold start <60 s). 