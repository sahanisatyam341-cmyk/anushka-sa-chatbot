import os
import requests
import streamlit as st

st.set_page_config(page_title="Anushka SA 😼", page_icon="😼", layout="centered")

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

PERSONAS = {
    "Hinglish + Bhojpuri 😼": 'Speak in casual Hinglish with light Bhojpuri slang ("Ka ho bhaiya", "Booyah pakka ba", "Tension mat lo baby 🍼").',
    "Pure Bhojpuri 🌾": "Speak in fun Bhojpuri written in Roman script, like a desi gamer.",
    "Gamer English 🎮": 'Speak in energetic gamer English with a sprinkle of "Booyah!".',
}
MODES = {
    "Gaming 🎮": "Focus on Billa Royale / Free Fire: Bermuda locations (Clock Tower, Peak, Mill), gun combos, gloo wall rushes, headshot sensitivity.",
    "Padhai 📚": "Focus on study help: explain math, science and code step by step in a simple, fun way.",
    "Masti 😂": "Focus on friendly, funny, general chat.",
}
QUICK = ["🎮 Bermuda Tips", "🔥 Best Squad Setup", "🎯 Headshot Tips", "🧠 Math ka doubt hai"]


def get_key():
    for name in ("GROQ_API_KEY", "GEMINI_API_KEY"):
        try:
            if name in st.secrets:
                return st.secrets[name]
        except Exception:
            pass
        if os.environ.get(name):
            return os.environ[name]
    return ""


def ask_ai(history, persona, mode, temperature):
    system = (
        'You are "Anushka SA" 😼, a confident, funny, friendly gamer assistant for the game Billa Royale (Free Fire style, Bermuda map). '
        f"{PERSONAS[persona]} {MODES[mode]} "
        'Keep replies punchy (under ~150 words), use short lines, "•" bullets, **bold** for key terms and emojis like 😼🍼🏆🔥💥🎮.'
    )
    messages = [{"role": "system", "content": system}] + [
        {"role": m["role"], "content": m["content"]} for m in history[-12:]
    ]
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {get_key()}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages, "temperature": temperature},
        timeout=60,
    )
    data = r.json()
    if not r.ok:
        raise RuntimeError(data.get("error", {}).get("message", f"HTTP {r.status_code}"))
    return data["choices"][0]["message"]["content"]


# ---------- Sidebar ----------
with st.sidebar:
    st.title("Anushka SA 😼")
    persona = st.selectbox("Persona Style", list(PERSONAS))
    mode = st.radio("Mode", list(MODES))
    temperature = st.slider("Masti level 🔥", 0.0, 1.5, 0.9, 0.1)
    if st.button("🗑️ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    if st.session_state.get("messages"):
        text = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages)
        st.download_button("⬇️ Chat download", text, "anushka_chat.txt", use_container_width=True)

# ---------- Chat ----------
st.title("Anushka SA 👑")
st.caption("BOOYAH MASTER • Gaming, padhai aur masti — sab poochho!")

if not get_key():
    st.warning("API key set nahi hai. App Settings → Secrets mein `GROQ_API_KEY` daalo. 🔑")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar="😼" if m["role"] == "assistant" else None):
        st.markdown(m["content"])

if not st.session_state.messages:
    st.info("Ka ho bhaiya! Sab Thik Thak? 🍼 Neeche se kuch chuno ya khud likho.")
    cols = st.columns(2)
    for i, q in enumerate(QUICK):
        if cols[i % 2].button(q, use_container_width=True):
            st.session_state.pending = q
            st.rerun()

prompt = st.chat_input("Anushka se kuch poochho baby... (e.g. Peak par kaise rush kare?)")
prompt = prompt or st.session_state.pop("pending", None)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="😼"):
        if not get_key():
            reply = "Pehle API key daalo bhaiya, tab hum baat karenge! 🔑😼"
        else:
            try:
                with st.spinner("Anushka likh rahi hai..."):
                    reply = ask_ai(st.session_state.messages, persona, mode, temperature)
            except Exception as e:
                reply = f"Arey bhaiya, network ne hag diya! 😼💥\n\n`{e}`"
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    
