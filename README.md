# Anushka SA 😼 — Billa Royale AI Chatbot

Gaming tips, padhai ka help aur masti — Hinglish/Bhojpuri persona ke saath.

## Files
- `app.py` — Streamlit app (real AI, Gemini)
- `Anushka_SA_Chatbot.html` — standalone offline demo (no key needed)

## Run locally
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then add your key
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)
1. Push this repo to GitHub (secrets.toml is git-ignored — never commit your key).
2. share.streamlit.io → New app → pick repo, branch, `app.py`.
3. App → Settings → Secrets → add: `GEMINI_API_KEY = "your-key"`
4. Optional secret/env: `GEMINI_MODEL` (default `gemini-2.5-flash`).

Get a free key: https://aistudio.google.com/apikey
