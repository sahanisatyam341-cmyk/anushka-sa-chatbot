import base64
import io
import os
import re

import requests
import streamlit as st
from PIL import Image

# ============================================================
# Anushka SA — Advanced v5.4.4 Vision & Uncapped Edition 😼🔥
# ============================================================

st.set_page_config(
    page_title="Anushka SA v5.4.4 Uncapped 😼🔥",
    page_icon="😼",
    layout="centered",
)

GROQ_URL = "https://api.groq.com/openai/v1"
PREFERRED_MODELS = [
    "llama-3.2-11b-vision-preview",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

PERSONAS = {
    "Hinglish + Bhojpuri 😼": (
        'Use casual Hinglish with light Bhojpuri phrases like "Ka ho" and '
        '"Booyah pakka ba". Be friendly, playful, and clear, just like a true friend.'
    ),
    "Pure Bhojpuri 🌾": (
        "Use fun Bhojpuri in Roman script, like a friendly desi gamer."
    ),
    "Gamer English 🎮": (
        'Use energetic gamer English with a little "Booyah!".'
    ),
}

MODES = {
    "Coding & Tech 💻": (
        "Focus on writing clean, runnable code, fixing errors/bugs, "
        "Termux commands, and web development step by step."
    ),
    "Gaming 🎮": (
        "Focus on Free Fire/Battle Royale tips, map strategy, and tactics."
    ),
    "Padhai 📚": (
        "Explain school subjects and math clearly with examples."
    ),
    "Masti 😂": (
        "Focus on friendly, funny, general conversation."
    ),
}

QUICK_PROMPTS = [
    "💻 Code Error Fix karo",
    "🎮 Bermuda Tips",
    "🔥 Best Squad Setup",
    "🧠 Math ka doubt hai",
]

MODE_TEMPERATURE = {
    "Coding & Tech 💻": 0.3,
    "Gaming 🎮": 0.8,
    "Padhai 📚": 0.2,
    "Masti 😂": 0.9,
}

ACCENTS = {
    "Indian 🇮🇳": "co.in",
    "US 🇺🇸": "com",
    "UK 🇬🇧": "co.uk",
}


def get_secret(*names):
    for name in names:
        try:
            value = st.secrets.get(name, "")
            if value:
                return str(value).strip()
        except Exception:
            pass
        value = os.environ.get(name, "")
        if value:
            return value.strip()
    return ""


GROQ_KEY = get_secret("GROQ_API_KEY")
SUPABASE_URL = get_secret("SUPABASE_URL").rstrip("/")
SUPABASE_ANON_KEY = get_secret("SUPABASE_ANON_KEY")


# -------------------- Appearance --------------------
def apply_style():
    try:
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bg.jpg")
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("ascii")
        background = (
            "linear-gradient(rgba(2,6,23,.60), rgba(2,6,23,.90)), "
            f"url(data:image/jpeg;base64,{encoded})"
        )
    except Exception:
        background = "#020617"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {background};
            background-size: cover;
            background-position: center top;
            background-attachment: fixed;
        }}
        header[data-testid="stHeader"] {{ background: transparent; }}
        section[data-testid="stSidebar"] > div {{
            background: rgba(2,6,23,.95);
            backdrop-filter: blur(10px);
        }}
        [data-testid="stChatMessage"] {{
            background: rgba(15,23,42,.85);
            border-radius: 14px;
            border: 1px solid rgba(56,189,248,0.2);
        }}
        h1, h2, h3, label, [data-testid="stCaptionContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li {{
            color: #f1f5f9 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_style()


# -------------------- Supabase helpers --------------------
def response_error(response):
    try:
        data = response.json()
        if isinstance(data, dict):
            error = data.get("msg") or data.get("message") or data.get("error")
            if error:
                return str(error)
        return str(data)
    except Exception:
        return f"HTTP {response.status_code}"


def require_supabase():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("Supabase secrets missing hain.")


def auth_call(path, payload, params=None):
    require_supabase()
    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/{path}",
        params=params,
        json=payload,
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(response_error(response))
    return response.json()


def set_session(data):
    st.session_state.token = data["access_token"]
    st.session_state.refresh = data.get("refresh_token")
    st.session_state.user = data.get("user", {})


def logout():
    for key in ("user", "token", "refresh", "chat_id", "messages", "chats", "memories", "pending"):
        st.session_state.pop(key, None)


def db(method, table, params=None, body=None, returning=False):
    require_supabase()
    token = st.session_state.get("token")
    if not token:
        raise RuntimeError("Session expire ho gaya. Login karo.")

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if returning:
        headers["Prefer"] = "return=representation"

    response = requests.request(
        method, f"{SUPABASE_URL}/rest/v1/{table}", params=params, json=body, headers=headers, timeout=30
    )
    if not response.ok:
        raise RuntimeError(response_error(response))
    return response.json() if response.text else None


# -------------------- Login / Signup --------------------
def login_page():
    st.title("Anushka SA v5.4.4 👑")
    st.caption("VISION & UNCAFFED MASTER • Login Portal")

    if not (SUPABASE_URL and SUPABASE_ANON_KEY):
        st.error("Supabase URL aur Anon Key secrets mein set nahi hain.")
        st.stop()

    login_tab, signup_tab = st.tabs(["Login", "Signup"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login_clicked = st.form_submit_button("Login", use_container_width=True)

        if login_clicked:
            try:
                data = auth_call("token", {"email": email.strip(), "password": password}, {"grant_type": "password"})
                set_session(data)
                st.rerun()
            except Exception as error:
                st.error(f"Login nahi hua: {error}")

    with signup_tab:
        with st.form("signup_form"):
            signup_email = st.text_input("Email", key="s_email")
            p1 = st.text_input("Password (min 6 chars)", type="password", key="s_p1")
            p2 = st.text_input("Confirm Password", type="password", key="s_p2")
            signup_clicked = st.form_submit_button("Naya Account Banao", use_container_width=True)

        if signup_clicked:
            if len(p1) < 6:
                st.error("Password kam se kam 6 characters ka hona chahiye.")
            elif p1 != p2:
                st.error("Passwords match nahi karte.")
            else:
                try:
                    data = auth_call("signup", {"email": signup_email.strip(), "password": p1})
                    if data.get("access_token"):
                        set_session(data)
                        st.rerun()
                    else:
                        st.success("Account ban gaya! Ab login karo.")
                except Exception as error:
                    st.error(f"Signup error: {error}")

    st.stop()


# -------------------- Chats & Memory --------------------
def load_chats():
    rows = db("GET", "anushka_chats", {"select": "id,title", "order": "created_at.desc", "limit": "40"})
    st.session_state.chats = rows or []


def open_chat(chat_id):
    rows = db("GET", "anushka_messages", {"select": "role,content", "chat_id": f"eq.{chat_id}", "order": "id.asc"})
    st.session_state.chat_id = chat_id
    st.session_state.messages = [{"role": r["role"], "content": r["content"]} for r in (rows or [])]


def new_chat():
    st.session_state.chat_id = None
    st.session_state.messages = []


def save_message(role, content):
    if st.session_state.get("chat_id") is None:
        rows = db("POST", "anushka_chats", body={"title": content[:40]}, returning=True)
        if rows:
            st.session_state.chat_id = rows[0]["id"]
            load_chats()
    if st.session_state.get("chat_id"):
        db("POST", "anushka_messages", body={"chat_id": st.session_state.chat_id, "role": role, "content": content})


def load_memories():
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        st.session_state.memories = []
        return
    rows = db("GET", "anushka_memory", {"select": "id,memory", "user_id": f"eq.{user_id}", "order": "created_at.desc", "limit": "20"})
    st.session_state.memories = rows or []


def save_memory(mem_text):
    user_id = st.session_state.get("user", {}).get("id")
    if user_id and mem_text.strip():
        db("POST", "anushka_memory", body={"user_id": user_id, "memory": mem_text.strip()})
        load_memories()


def delete_memory(mem_id):
    db("DELETE", "anushka_memory", {"id": f"eq.{mem_id}"})
    load_memories()


# -------------------- AI & Vision --------------------
@st.cache_data(ttl=600, show_spinner=False)
def list_models(api_key):
    if not api_key:
        return PREFERRED_MODELS
    try:
        res = requests.get(f"{GROQ_URL}/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
        if res.ok:
            ids = [i["id"] for i in res.json().get("data", [])]
            vision_models = [m for m in ids if "vision" in m.lower() or "llava" in m.lower()]
            other_models = [m for m in ids if not any(x in m.lower() for x in ("whisper", "tts", "embed", "vision", "llava"))]
            return vision_models + PREFERRED_MODELS + other_models
    except Exception:
        pass
    return PREFERRED_MODELS


def ask_ai(history, model, persona, mode, temp, memories, image_bytes=None):
    mem_ctx = "\n".join(f"- {m['memory']}" for m in memories) if memories else ""
    sys_prompt = (
        'You are "Anushka SA v5.4.4" 😼, a loving, playful, and super smart AI companion and coding/gaming expert. '
        "Always reply in a warm, friendly tone with engaging Hinglish and Bhojpuri flavor like 'Ka ho babu, sab thik-thak?'. "
        f"Style: {PERSONAS[persona]} Mode: {MODES[mode]} "
        "If an image or code error screenshot is provided, examine it deeply, understand the bug, and provide a clear, clean solution. "
        f"Memory context: {mem_ctx}"
    )

    messages = [{"role": "system", "content": sys_prompt}]
    
    # Keeping history optimized to prevent token limit errors
    for idx, h in enumerate(history[-10:]):
        role = h.get("role")
        content = h.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            if idx == len(history[-10:]) - 1 and image_bytes and role == "user":
                encoded_image = base64.b64encode(image_bytes).decode("utf-8")
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": content},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                    ]
                })
            else:
                messages.append({"role": role, "content": content})

    active_model = model
    if image_bytes and "vision" not in active_model.lower():
        active_model = "llama-3.2-11b-vision-preview"

    res = requests.post(
        f"{GROQ_URL}/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
        json={"model": active_model, "messages": messages, "temperature": temp, "max_tokens": 2048},
        timeout=60,
    )
    if not res.ok:
        raise RuntimeError(f"Groq API Error: {res.text}")
    return res.json()["choices"][0]["message"]["content"].strip()


@st.cache_data(show_spinner=False, max_entries=30)
def tts_bytes(text, tld, slow):
    from gtts import gTTS
    clean = re.sub(r"[*_`#>•\U0001F000-\U0001FAFF]", "", text).strip()[:500]
    buf = io.BytesIO()
    gTTS(clean, lang="hi" if re.search(r"[\u0900-\u097F]", clean) else "en", tld=tld, slow=slow).write_to_fp(buf)
    return buf.getvalue()


# ==================== MAIN APP FLOW ====================
if "user" not in st.session_state:
    login_page()

if "messages" not in st.session_state:
    new_chat()

try:
    if "chats" not in st.session_state:
        load_chats()
    if "memories" not in st.session_state:
        load_memories()
except Exception:
    st.session_state.chats = []
    st.session_state.memories = []

available_models = list_models(GROQ_KEY) if GROQ_KEY else PREFERRED_MODELS
model = available_models[0] if available_models else "llama-3.2-11b-vision-preview"

with st.sidebar:
    st.markdown(f"**👤 {st.session_state.user.get('email', 'User')}**")
    st.caption("Engine: v5.4.4 Uncapped 🚀")

    if st.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()

    if st.button("➕ Nayi Chat", use_container_width=True, type="primary"):
        new_chat()
        st.rerun()

    st.markdown("### Chat History 🕘")
    for chat in st.session_state.get("chats", []):
        if st.button(f"💬 {(chat.get('title') or 'Chat')[:30]}", key=f"c_{chat['id']}", use_container_width=True):
            open_chat(chat["id"])
            st.rerun()

    with st.expander("⚙️ Settings (Vision & Uncapped)"):
        persona = st.selectbox("Persona", list(PERSONAS))
        mode = st.radio("Mode", list(MODES))
        temp = st.slider("Masti 🔥", 0.0, 1.5, MODE_TEMPERATURE[mode], 0.1)
        model = st.selectbox("AI Model", available_models, index=0)
        voice_on = st.toggle("Anushka Bole 🎙️", value=True)
        accent = st.selectbox("Accent", list(ACCENTS))
        slow = st.toggle("Dheere bolo", value=False)

st.title("Anushka SA v5.4.4 👑")
st.caption("VISION & UNCAFFED MASTER • Photo upload karo aur unlimited chat karo!")

# File uploader for images / screenshots
uploaded_file = st.file_uploader("📸 Error ya Code ka Screenshot yahan upload karo:", type=["png", "jpg", "jpeg"])
image_bytes = None
if uploaded_file is not None:
    image_bytes = uploaded_file.read()
    st.image(image_bytes, caption="Uploaded Image / Error Screenshot", use_container_width=True)

# Render existing chat messages
for msg in st.session_state.get("messages", []):
    with st.chat_message(msg["role"], avatar="😼" if msg["role"] == "assistant" else None):
        st.markdown(msg["content"])

if not st.session_state.get("messages"):
    st.info("Ka ho babu! Photo bhejo ya kuch bhi pucho, Anushka ekdam tayar hai! 😼🔥")
    cols = st.columns(2)
    for i, q in enumerate(QUICK_PROMPTS):
        if cols[i % 2].button(q, use_container_width=True, key=f"qp_{i}"):
            st.session_state.pending = q
            st.rerun()

prompt = st.chat_input("Anushka se kuch poochho ya error share karo... 💻")
prompt = prompt or st.session_state.pop("pending", None)

if prompt:
    full_prompt = prompt
    st.session_state.messages.append({"role": "user", "content": full_prompt})
    with st.chat_message("user"):
        st.markdown(full_prompt)
    try:
        save_message("user", full_prompt)
    except Exception:
        pass

    with st.chat_message("assistant", avatar="😼"):
        try:
            with st.spinner("Anushka soch rahi hai aur file/photo check kar rahi hai... 🧠"):
                reply = ask_ai(
                    st.session_state.messages, 
                    model, 
                    persona, 
                    mode, 
                    temp, 
                    st.session_state.get("memories", []),
                    image_bytes=image_bytes
                )
        except Exception as e:
            reply = f"Arey babu error aa gaya: `{e}`"
        st.markdown(reply)

        if voice_on:
            try:
                audio = tts_bytes(reply, ACCENTS[accent], slow)
                st.audio(audio, format="audio/mp3", autoplay=True)
            except Exception:
                pass

    st.session_state.messages.append({"role": "assistant", "content": reply})
    try:
        save_message("assistant", reply)
    except Exception:
        pass
