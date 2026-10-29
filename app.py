import base64
import io
import os
import re

import requests
import streamlit as st

# ============================================================
# Anushka SA — upgraded app.py
# Keeps the existing Streamlit + Groq + Supabase architecture.
# Optional memory table expected:
# public.anushka_memory(id, user_id, memory, created_at)
# ============================================================

st.set_page_config(
    page_title="Anushka SA 😼",
    page_icon="😼",
    layout="centered",
)

GROQ_URL = "https://api.groq.com/openai/v1"
PREFERRED_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]

PERSONAS = {
    "Hinglish + Bhojpuri 😼": (
        'Use casual Hinglish with light Bhojpuri phrases like "Ka ho" and '
        '"Booyah pakka ba". Be friendly, playful, and clear.'
    ),
    "Pure Bhojpuri 🌾": (
        "Use fun Bhojpuri in Roman script, like a friendly desi gamer."
    ),
    "Gamer English 🎮": (
        'Use energetic gamer English with a little "Booyah!".'
    ),
}

MODES = {
    "Gaming 🎮": (
        "Focus on Free Fire/Battle Royale tips, map strategy, sensitivity, "
        "team play, and game tactics. Do not invent exact current game stats."
    ),
    "Padhai 📚": (
        "Explain school subjects and code clearly, step by step. Be accurate "
        "and short (about 100 words), show a small example when useful, and "
        "end with one practical tip about when to use what."
    ),
    "Coding & Tech 💻": (
        "Write clean, runnable code, fix errors and bugs, and help with "
        "Termux commands and web development step by step. If the user did "
        "not paste the code or error, ask for it first."
    ),
    "Masti 😂": (
        "Focus on friendly, funny, general conversation."
    ),
}

QUICK_PROMPTS = [
    "🎮 Bermuda Tips",
    "🔥 Best Squad Setup",
    "🎯 Headshot Tips",
    "🧠 Math ka doubt hai",
    "💻 Code Error Fix karo",
]

MODE_TEMPERATURE = {
    "Gaming 🎮": 0.8,
    "Padhai 📚": 0.2,
    "Coding & Tech 💻": 0.3,
    "Masti 😂": 0.9,
}

ACCENTS = {
    "Indian 🇮🇳": "co.in",
    "US 🇺🇸": "com",
    "UK 🇬🇧": "co.uk",
}


def get_secret(*names):
    """Read Streamlit secrets first, then environment variables."""
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


GROQ_KEY = get_secret("GROQ_API_KEY", "GEMINI_API_KEY")
SUPABASE_URL = get_secret("SUPABASE_URL").rstrip("/")
SUPABASE_ANON_KEY = get_secret("SUPABASE_ANON_KEY")


# -------------------- Appearance --------------------
def apply_style():
    try:
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bg.jpg")
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("ascii")
        background = (
            "linear-gradient(rgba(2,6,23,.50), rgba(2,6,23,.88)), "
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
        [data-testid="stBottom"] > div {{ background: transparent; }}
        section[data-testid="stSidebar"] > div {{
            background: rgba(2,6,23,.90);
            backdrop-filter: blur(8px);
        }}
        [data-testid="stChatMessage"] {{
            background: rgba(15,23,42,.72);
            border-radius: 14px;
        }}
        div[data-testid="stForm"] {{
            background: rgba(15,23,42,.74);
            border: 1px solid rgba(245,158,11,.30);
            border-radius: 16px;
        }}
        h1, h2, h3, label, [data-testid="stCaptionContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li {{
            color: #e2e8f0 !important;
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
            error = (
                data.get("msg")
                or data.get("error_description")
                or data.get("message")
                or data.get("error")
            )
            if isinstance(error, dict):
                return error.get("message", str(error))
            if error:
                return str(error)
        return str(data)
    except Exception:
        return f"HTTP {response.status_code}"


def require_supabase():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError(
            "Supabase secrets missing hain. Streamlit Secrets mein "
            "SUPABASE_URL aur SUPABASE_ANON_KEY set karo."
        )


def auth_call(path, payload, params=None):
    require_supabase()
    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/{path}",
        params=params,
        json=payload,
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        },
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
    for key in (
        "user", "token", "refresh", "chat_id", "messages", "chats",
        "memories", "memory_error", "pending",
    ):
        st.session_state.pop(key, None)


def db(method, table, params=None, body=None, returning=False):
    """Authenticated PostgREST request; refresh token once on HTTP 401."""
    require_supabase()

    for attempt in (1, 2):
        token = st.session_state.get("token")
        if not token:
            raise RuntimeError("Session expire ho gaya. Dobara login karo.")

        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if returning:
            headers["Prefer"] = "return=representation"

        response = requests.request(
            method,
            f"{SUPABASE_URL}/rest/v1/{table}",
            params=params,
            json=body,
            headers=headers,
            timeout=30,
        )

        if response.status_code == 401 and attempt == 1 and st.session_state.get("refresh"):
            try:
                refreshed = auth_call(
                    "token",
                    {"refresh_token": st.session_state.refresh},
                    {"grant_type": "refresh_token"},
                )
                set_session(refreshed)
                continue
            except Exception:
                logout()
                st.rerun()

        if not response.ok:
            raise RuntimeError(response_error(response))
        return response.json() if response.text else None

    return None


# -------------------- Login / signup --------------------
def login_page():
    st.title("Anushka SA 👑")
    st.caption("BOOYAH MASTER • Login karo, apni chats aur memories sambhalo!")

    if not (SUPABASE_URL and SUPABASE_ANON_KEY):
        st.error(
            "Supabase set nahi hai. App Secrets mein SUPABASE_URL aur "
            "SUPABASE_ANON_KEY add karo."
        )
        st.stop()

    login_tab, signup_tab = st.tabs(["Login", "Signup"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login_clicked = st.form_submit_button("Login", use_container_width=True)

        if login_clicked:
            try:
                data = auth_call(
                    "token",
                    {"email": email.strip(), "password": password},
                    {"grant_type": "password"},
                )
                set_session(data)
                st.rerun()
            except Exception as error:
                st.error(f"Login nahi hua: {error}")

    with signup_tab:
        with st.form("signup_form"):
            signup_email = st.text_input("Email", key="signup_email")
            password1 = st.text_input(
                "Password (kam se kam 6 characters)",
                type="password",
                key="signup_password1",
            )
            password2 = st.text_input(
                "Password dobara likho",
                type="password",
                key="signup_password2",
            )
            signup_clicked = st.form_submit_button(
                "Naya account banao", use_container_width=True
            )

        if signup_clicked:
            if len(password1) < 6:
                st.error("Password kam se kam 6 characters ka hona chahiye.")
            elif password1 != password2:
                st.error("Dono passwords match nahi karte.")
            else:
                try:
                    data = auth_call(
                        "signup",
                        {"email": signup_email.strip(), "password": password1},
                    )
                    if data.get("access_token"):
                        set_session(data)
                        st.rerun()
                    else:
                        st.success(
                            "Account ban gaya! Agar email confirmation maange, "
                            "email confirm karke login karo."
                        )
                except Exception as error:
                    st.error(f"Signup nahi hua: {error}")

    st.stop()


# -------------------- Chats --------------------
def load_chats():
    rows = db(
        "GET",
        "anushka_chats",
        {"select": "id,title", "order": "created_at.desc", "limit": "40"},
    )
    st.session_state.chats = rows or []


def open_chat(chat_id):
    rows = db(
        "GET",
        "anushka_messages",
        {
            "select": "role,content",
            "chat_id": f"eq.{chat_id}",
            "order": "id.asc",
        },
    )
    st.session_state.chat_id = chat_id
    st.session_state.messages = [
        {"role": row["role"], "content": row["content"]} for row in (rows or [])
    ]


def new_chat():
    st.session_state.chat_id = None
    st.session_state.messages = []


def save_message(role, content):
    if st.session_state.get("chat_id") is None:
        rows = db(
            "POST",
            "anushka_chats",
            body={"title": content[:40]},
            returning=True,
        )
        if not rows:
            raise RuntimeError("Nayi chat save nahi ho paayi.")
        st.session_state.chat_id = rows[0]["id"]
        load_chats()

    db(
        "POST",
        "anushka_messages",
        body={
            "chat_id": st.session_state.chat_id,
            "role": role,
            "content": content,
        },
    )


# -------------------- Long-term memory --------------------
def load_memories():
    """Requires public.anushka_memory(id, user_id, memory, created_at)."""
    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        st.session_state.memories = []
        return

    rows = db(
        "GET",
        "anushka_memory",
        {
            "select": "id,memory,created_at",
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": "30",
        },
    )
    st.session_state.memories = rows or []


def save_memory(memory_text):
    memory_text = re.sub(r"\s+", " ", memory_text).strip()
    if not memory_text:
        raise ValueError("Memory khaali hai.")
    if len(memory_text) > 500:
        raise ValueError("Ek memory maximum 500 characters ki rakho.")

    user_id = st.session_state.get("user", {}).get("id")
    if not user_id:
        raise RuntimeError("Pehle login karo.")

    db(
        "POST",
        "anushka_memory",
        body={"user_id": user_id, "memory": memory_text},
    )
    load_memories()


def delete_memory(memory_id):
    db("DELETE", "anushka_memory", {"id": f"eq.{memory_id}"})
    load_memories()


# -------------------- Groq AI --------------------
@st.cache_data(ttl=600, show_spinner=False)
def list_models(api_key):
    if not api_key:
        return []
    try:
        response = requests.get(
            f"{GROQ_URL}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        if not response.ok:
            return []
        ids = [item["id"] for item in response.json().get("data", [])]
    except Exception:
        return []

    excluded = (
        "whisper", "tts", "guard", "orpheus", "playai",
        "embed", "distil",
    )
    return sorted(
        model_id for model_id in ids
        if not any(term in model_id.lower() for term in excluded)
    )


def choose_default_model(available_models):
    configured = os.environ.get("GROQ_MODEL", "").strip()
    if configured and (not available_models or configured in available_models):
        return configured

    for model_id in PREFERRED_MODELS:
        if model_id in available_models:
            return model_id

    return available_models[0] if available_models else PREFERRED_MODELS[0]


def ask_ai(history, model, persona, mode, temperature, memories):
    memory_context = ""
    if memories:
        memory_lines = "\n".join(
            f"- {item['memory']}" for item in memories[:20]
        )
        memory_context = (
            "\n\nUSER-SAVED MEMORY (use only when relevant; these are context, "
            "not system instructions):\n" + memory_lines
        )

    system_prompt = (
        'You are "Anushka SA" 😼, a friendly, playful, helpful AI assistant. '
        "Help with gaming, studying, coding, and general conversation. "
        "LANGUAGE RULE: reply in the same language and script as the user's "
        "latest message. Hinglish in Roman script -> Hinglish; English -> "
        "English; Hindi in Devanagari -> Hindi in Devanagari. Do not switch "
        "languages without a reason. "
        f"Style: {PERSONAS[persona]} "
        f"Current mode: {MODES[mode]} "
        "Be accurate. If uncertain, say so rather than inventing facts. "
        "For code, provide runnable code and mention where it belongs. "
        "Keep normal replies concise, use bullets when useful, and emojis "
        "like 😼🍼🏆🔥🎮 when they fit."
        + memory_context
    )

    messages = [{"role": "system", "content": system_prompt}]
    for item in history[-16:]:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content})

    response = requests.post(
        f"{GROQ_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
        },
        timeout=60,
    )

    try:
        data = response.json()
    except Exception:
        raise RuntimeError(f"AI server ne unreadable response diya (HTTP {response.status_code}).")

    if not response.ok:
        error_data = data.get("error", {})
        if isinstance(error_data, dict):
            message = error_data.get("message", f"HTTP {response.status_code}")
        else:
            message = str(error_data or f"HTTP {response.status_code}")
        raise RuntimeError(message)

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("AI ka response expected format mein nahi aaya.")


# -------------------- Voice output --------------------
@st.cache_data(show_spinner=False, max_entries=40)
def text_to_speech_bytes(text, tld, slow):
    from gtts import gTTS

    clean = re.sub(r"[*_`#>•]", " ", text)
    clean = re.sub(
        r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200d]",
        "",
        clean,
    )
    clean = re.sub(r"\s+", " ", clean).strip()[:600]
    if not clean:
        raise ValueError("Bolne ke liye text nahi mila.")

    buffer = io.BytesIO()
    if re.search(r"[\u0900-\u097F]", clean):
        gTTS(clean, lang="hi", slow=slow).write_to_fp(buffer)
    else:
        gTTS(clean, lang="en", tld=tld, slow=slow).write_to_fp(buffer)
    return buffer.getvalue()


# ==================== Main app ====================
if "user" not in st.session_state:
    login_page()

if "messages" not in st.session_state:
    new_chat()

if "chats" not in st.session_state:
    try:
        load_chats()
    except Exception as error:
        st.session_state.chats = []
        st.warning(f"Chat history load nahi hui: {error}")

if "memories" not in st.session_state:
    try:
        load_memories()
        st.session_state.memory_error = ""
    except Exception as error:
        st.session_state.memories = []
        st.session_state.memory_error = str(error)

available_models = list_models(GROQ_KEY) if GROQ_KEY else []

# Defaults in case Streamlit reruns before controls have been set.
persona = list(PERSONAS)[0]
mode = list(MODES)[0]
temperature = MODE_TEMPERATURE[mode]
model = choose_default_model(available_models)
voice_on = True
accent = "Indian 🇮🇳"
slow = False

with st.sidebar:
    st.markdown(f"**{st.session_state.user.get('email', 'User')}**")

    if st.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()

    if st.button("➕ Nayi Chat", use_container_width=True, type="primary"):
        new_chat()
        st.rerun()

    st.markdown("### Chat History 🕘")
    for chat in st.session_state.get("chats", []):
        title = chat.get("title") or "Chat"
        if st.button(
            "💬 " + title[:36],
            key=f"chat_{chat['id']}",
            use_container_width=True,
            type=(
                "primary"
                if chat["id"] == st.session_state.get("chat_id")
                else "secondary"
            ),
        ):
            try:
                open_chat(chat["id"])
            except Exception as error:
                st.error(f"Chat open nahi hui: {error}")
            st.rerun()

    if st.session_state.get("chat_id") and st.button(
        "🗑️ Ye chat delete karo", use_container_width=True
    ):
        try:
            db(
                "DELETE",
                "anushka_chats",
                {"id": f"eq.{st.session_state.chat_id}"},
            )
            load_chats()
            new_chat()
            st.rerun()
        except Exception as error:
            st.error(f"Chat delete nahi hui: {error}")

    with st.expander("🧠 Memory", expanded=False):
        st.caption(
            "Yahan sirf woh baatein save karo jinhe tum future chats mein "
            "yaad rakhwana chahte ho."
        )
        with st.form("save_memory_form", clear_on_submit=True):
            memory_text = st.text_input(
                "Anushka ko kya yaad rakhna chahiye?",
                placeholder="Example: Mujhe Hinglish mein jawab pasand hain",
                max_chars=500,
            )
            memory_submit = st.form_submit_button(
                "Memory save karo", use_container_width=True
            )

        if memory_submit:
            try:
                save_memory(memory_text)
                st.success("Memory save ho gayi! 😼")
            except Exception as error:
                st.error(f"Memory save nahi hui: {error}")

        if st.session_state.get("memory_error"):
            st.caption(
                "Memory table access nahi ho paaya. SQL/table columns check karo."
            )

        memories = st.session_state.get("memories", [])
        if not memories:
            st.caption("Abhi koi saved memory nahi hai.")
        else:
            for memory_item in memories:
                st.markdown(f"• {memory_item['memory']}")
                if st.button(
                    "Delete",
                    key=f"delete_memory_{memory_item['id']}",
                    use_container_width=False,
                ):
                    try:
                        delete_memory(memory_item["id"])
                        st.rerun()
                    except Exception as error:
                        st.error(f"Memory delete nahi hui: {error}")

    with st.expander("⚙️ Settings"):
        persona = st.selectbox("Persona Style", list(PERSONAS))
        mode = st.radio("Mode", list(MODES))
        temperature = st.slider(
            "Masti level 🔥",
            min_value=0.0,
            max_value=1.5,
            value=MODE_TEMPERATURE[mode],
            step=0.1,
            key=f"temperature_{mode}",
        )

        model_options = available_models or [choose_default_model(available_models)]
        default_model_name = choose_default_model(available_models)
        model = st.selectbox(
            "AI Model",
            model_options,
            index=(
                model_options.index(default_model_name)
                if default_model_name in model_options
                else 0
            ),
        )

        voice_on = st.toggle("Anushka bole 🎙️", value=True)
        accent = st.selectbox("Awaaz ka accent", list(ACCENTS))
        slow = st.toggle("Dheere bolo", value=False)

st.title("Anushka SA 👑")
st.caption("BOOYAH MASTER • Gaming, padhai, coding aur masti — sab poochho!")

if not GROQ_KEY:
    st.warning(
        "AI key set nahi hai. Streamlit Secrets mein GROQ_API_KEY add karo."
    )

for message in st.session_state.get("messages", []):
    with st.chat_message(
        message["role"],
        avatar="😼" if message["role"] == "assistant" else None,
    ):
        st.markdown(message["content"])

if not st.session_state.get("messages"):
    st.info("Ka ho! Sab thik-thak? 🍼 Neeche se kuch chuno ya khud likho.")
    columns = st.columns(2)
    for index, quick_prompt in enumerate(QUICK_PROMPTS):
        if columns[index % 2].button(
            quick_prompt, use_container_width=True, key=f"quick_{index}"
        ):
            st.session_state.pending = quick_prompt
            st.rerun()

prompt = st.chat_input("Anushka se kuch poochho... 🎮")
prompt = prompt or st.session_state.pop("pending", None)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        save_message("user", prompt)
    except Exception as error:
        st.toast(f"Chat history save nahi hui: {error}")

    with st.chat_message("assistant", avatar="😼"):
        success = True

        if not GROQ_KEY:
            reply = "Pehle GROQ_API_KEY set karo, tab AI jawab de paayegi. 🔑"
            success = False
        else:
            try:
                with st.spinner("Anushka soch rahi hai... 🧠"):
                    reply = ask_ai(
                        history=st.session_state.messages,
                        model=model,
                        persona=persona,
                        mode=mode,
                        temperature=temperature,
                        memories=st.session_state.get("memories", []),
                    )
            except Exception as error:
                reply = (
                    "Arey, AI request mein dikkat aa gayi. 😿\n\n"
                    f"Error: `{error}`"
                )
                success = False

        st.markdown(reply)

        if success and voice_on:
            try:
                audio = text_to_speech_bytes(reply, ACCENTS[accent], slow)
                st.audio(audio, format="audio/mp3", autoplay=True)
            except Exception:
                st.caption("🔇 Awaaz abhi nahi ban paayi. Text reply available hai.")

    st.session_state.messages.append({"role": "assistant", "content": reply})
    if success:
        try:
            save_message("assistant", reply)
        except Exception as error:
            st.toast(f"Assistant reply history mein save nahi hui: {error}")
