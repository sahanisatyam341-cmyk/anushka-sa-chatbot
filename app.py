import json
import os

import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Anushka SA 😼", page_icon="😼", layout="centered")

API = "https://api.groq.com/openai/v1"
PREFERRED = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-20b", "openai/gpt-oss-120b"]

PERSONAS = {
    "Hinglish + Bhojpuri 😼": 'Speak in casual Hinglish with light Bhojpuri slang ("Ka ho", "Booyah pakka ba", "Tension mat lo baby 🍼").',
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


@st.cache_data(ttl=600, show_spinner=False)
def list_models(key):
    """Ask Groq which chat models this key can really use."""
    try:
        r = requests.get(f"{API}/models", headers={"Authorization": f"Bearer {key}"}, timeout=20)
        ids = [m["id"] for m in r.json().get("data", [])]
    except Exception:
        return []
    bad = ("whisper", "tts", "guard", "orpheus", "playai", "embed", "distil")
    return sorted(i for i in ids if not any(b in i for b in bad))


def default_model(available):
    env = os.environ.get("GROQ_MODEL")
    if env:
        return env
    for m in PREFERRED:
        if m in available:
            return m
    return available[0] if available else PREFERRED[0]


def ask_ai(history, model, persona, mode, temperature):
    system = (
        'You are "Anushka SA" 😼, a confident, funny, friendly gamer assistant for the game Billa Royale (Free Fire style, Bermuda map). '
        f"{PERSONAS[persona]} {MODES[mode]} "
        'Keep replies punchy (under ~120 words), short lines, "•" bullets, **bold** for key terms, emojis like 😼🍼🏆🔥💥🎮.'
    )
    messages = [{"role": "system", "content": system}] + [
        {"role": m["role"], "content": m["content"]} for m in history[-12:]
    ]
    r = requests.post(
        f"{API}/chat/completions",
        headers={"Authorization": f"Bearer {get_key()}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": temperature},
        timeout=60,
    )
    data = r.json()
    if not r.ok:
        raise RuntimeError(data.get("error", {}).get("message", f"HTTP {r.status_code}"))
    return data["choices"][0]["message"]["content"]


VOICE_HTML = """
<div style="font-family:sans-serif">
<button id="b" style="background:#f59e0b;color:#1a1205;border:0;border-radius:20px;padding:6px 14px;font-weight:700;cursor:pointer">🔊 Anushka ko suno</button>
<script>
const TEXT = __TEXT__, RATE = __RATE__, PITCH = __PITCH__;
const FEM = /female|heera|zira|neerja|veena|swara|priya|aria|jenny|samantha|hia|natasha|libby/i;
function pick() {
  const v = speechSynthesis.getVoices();
  const en = v.filter(x => /^en[-_]IN/i.test(x.lang)), hi = v.filter(x => /^hi/i.test(x.lang)), any = v.filter(x => /^en/i.test(x.lang));
  return en.find(x => FEM.test(x.name)) || hi.find(x => FEM.test(x.name)) || en[0] || any.find(x => FEM.test(x.name)) || any[0] || hi[0] || null;
}
function say() {
  try {
    speechSynthesis.cancel();
    const clean = TEXT.replace(/[*_`#>•]/g, " ").replace(/\\p{Extended_Pictographic}/gu, "").replace(/\\s+/g, " ").trim();
    const u = new SpeechSynthesisUtterance(clean), v = pick();
    if (v) { u.voice = v; u.lang = v.lang; } else { u.lang = "en-IN"; }
    u.rate = RATE; u.pitch = PITCH;
    speechSynthesis.speak(u);
  } catch (e) {}
}
document.getElementById("b").onclick = say;
speechSynthesis.onvoiceschanged = () => {};
say();
</script></div>
"""


def speak(text, rate, pitch):
    html = (
        VOICE_HTML.replace("__TEXT__", json.dumps(text).replace("</", "<\\/"))
        .replace("__RATE__", str(rate))
        .replace("__PITCH__", str(pitch))
    )
    components.html(html, height=45)


# ---------- Sidebar ----------
key = get_key()
available = list_models(key) if key else []
with st.sidebar:
    st.title("Anushka SA 😼")
    persona = st.selectbox("Persona Style", list(PERSONAS))
    mode = st.radio("Mode", list(MODES))
    temperature = st.slider("Masti level 🔥", 0.0, 1.5, 0.9, 0.1)
    options = available or [default_model(available)]
    model = st.selectbox("AI Model", options, index=options.index(default_model(available)) if default_model(available) in options else 0)
    st.markdown("**Voice 🎙️**")
    voice_on = st.toggle("Anushka bole (voice)", value=True)
    rate = st.slider("Speed", 0.7, 1.4, 1.0, 0.05)
    pitch = st.slider("Awaaz patli/moti", 0.8, 1.6, 1.2, 0.05)
    if st.button("🗑️ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    if st.session_state.get("messages"):
        text = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages)
        st.download_button("⬇️ Chat download", text, "anushka_chat.txt", use_container_width=True)

# ---------- Chat ----------
st.title("Anushka SA 👑")
st.caption("BOOYAH MASTER • Gaming, padhai aur masti — sab poochho!")

if not key:
    st.warning("API key set nahi hai. App Settings → Secrets mein `GROQ_API_KEY` daalo. 🔑")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar="😼" if m["role"] == "assistant" else None):
        st.markdown(m["content"])

if not st.session_state.messages:
    st.info("Ka ho! Sab Thik Thak? 🍼 Neeche se kuch chuno ya khud likho.")
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
        ok = True
        if not key:
            reply, ok = "Pehle API key daalo, tab hum baat karenge! 🔑😼", False
        else:
            try:
                with st.spinner("Anushka likh rahi hai..."):
                    reply = ask_ai(st.session_state.messages, model, persona, mode, temperature)
            except Exception as e:
                reply, ok = f"Arey, network ne hag diya! 😼💥\n\n`{e}`", False
        st.markdown(reply)
        if ok and voice_on:
            speak(reply, rate, pitch)
    st.session_state.messages.append({"role": "assistant", "content": reply})
