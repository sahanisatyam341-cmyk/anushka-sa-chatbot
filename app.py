import base64
import hashlib
import inspect
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

# Anushka ka logo (Mikasa 🥺) — app.py ke andar hi embedded hai, alag file ki zaroorat nahi.
LOGO_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAUDBAQEAwUEBAQFBQUGBwwIBwcHBw8LCwkMEQ8SEhEPERETFhwXExQaFRERGCEYGh0dHx8fExciJC"
    "IeJBweHx7/2wBDAQUFBQcGBw4ICA4eFBEUHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh7/wAARCAEA"
    "AQADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhBy"
    "JxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKT"
    "lJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAA"
    "AAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRom"
    "JygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExc"
    "bHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3vNGRTM0ma8w5C3bXMkMgZTwKuXN+LjGRtNZP40hzUOCbuNSa"
    "Lvn4PFXLW4jKHeeayIwSePWuo0vTYGt1kkXcWFRUSRcLydhdIYPIxUHA71pZOcAUsUSRLtRQo9qHYKuTxXNPe51JcqGSuUjZiOAK5zUNQZZyyf"
    "Lmr2r6hhDGnQ9TXNTyhmJNEIXepE5msJluFDMQWq7o4RZ8eWpJ/iNczHMVPBxU51doSCpxircH0JUtTtrgExEA4JFcVrCOs5VueagufENzIR+8"
    "bAqpNqilS8zgKBlmY4AHqTRClJO5UpJkTxoCcjmkjt1kbAPX0rmdS8WJO7Jotsb8DO64LeXbL/20P3v+Ag/WuG8SeMIY1ZNQ1qe+Y9bPTmMMAP"
    "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"
)

LOGO_URI = f"data:image/jpeg;base64,{LOGO_B64}"
try:
    from PIL import Image as _PILImage

    _logo_img = _PILImage.open(io.BytesIO(base64.b64decode(LOGO_B64)))
    _small = io.BytesIO()
    _logo_img.resize((96, 96)).save(_small, format="JPEG", quality=85)
    AVATAR = "data:image/jpeg;base64," + base64.b64encode(_small.getvalue()).decode("ascii")
    PAGE_ICON = _logo_img
except Exception:
    AVATAR = "😼"
    PAGE_ICON = "😼"

st.set_page_config(
    page_title="Anushka SA",
    page_icon=PAGE_ICON,
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


GROQ_KEY = get_secret("GROQ_API_KEY")
GEMINI_KEY = get_secret("GEMINI_API_KEY")
# Gemini 3 Flash (text + photo). Secrets mein GEMINI_MODEL set ho to wahi chalega.
GEMINI_LABEL = "Gemini 3.9"  # top dropdown mein yehi naam dikhega
GEMINI_MODEL = os.environ.get("GEMINI_MODEL") or get_secret("GEMINI_MODEL") or "gemini-3-flash-preview"
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

        /* ---------- Folax-style UI ---------- */
        .hero {{ text-align: center; padding: 2rem 0 1rem; }}
        .hero img {{
            width: 132px; height: 132px; border-radius: 50%; object-fit: cover;
            box-shadow: 0 0 0 4px rgba(255,255,255,.10),
                        0 0 48px rgba(244,114,182,.45),
                        0 0 90px rgba(56,189,248,.25);
        }}
        .hero-title {{
            margin-top: 1rem; font-size: 1.7rem; font-weight: 800;
            background: linear-gradient(90deg,#7dd3fc,#c4b5fd,#f9a8d4);
            -webkit-background-clip: text; background-clip: text;
            color: transparent !important;
        }}
        .hero-sub {{ color: #94a3b8; margin-top: .2rem; }}

        .st-key-model_bar {{ max-width: 300px; margin: 0 auto; }}
        .st-key-model_bar [data-baseweb="select"] > div {{
            background: rgba(15,23,42,.65);
            border: 1px solid rgba(255,255,255,.14);
            border-radius: 999px; font-weight: 700;
        }}

        .side-title {{ font-size: .95rem; color: #94a3b8; margin: .2rem 0 .5rem .4rem; }}
        .month-label {{
            color: #94a3b8; font-size: .8rem; font-weight: 700;
            margin: .5rem 0 .1rem .5rem;
        }}
        .st-key-hist_card {{
            background: rgba(255,255,255,.96); border-radius: 22px;
            padding: .7rem .5rem; max-height: 62vh; overflow-y: auto;
        }}
        .st-key-hist_card button {{
            background: transparent !important; border: none !important;
            box-shadow: none !important; justify-content: flex-start;
            min-height: 0; padding: .45rem .5rem;
        }}
        .st-key-hist_card button[data-testid="stBaseButton-primary"] {{
            background: rgba(2,6,23,.08) !important;
        }}
        .st-key-hist_card button p,
        .st-key-hist_card [data-testid="stMarkdownContainer"] p {{
            color: #0f172a !important; font-weight: 700; text-align: left;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .st-key-hist_card [data-testid="stCaptionContainer"] {{ color: #64748b !important; }}

        [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"],
        [data-testid="stSidebarUserContent"] > div {{ min-height: calc(100vh - 6rem); }}
        .st-key-side_bottom {{
            position: sticky; bottom: 0; margin-top: auto; z-index: 5;
            padding: .6rem 0 .3rem;
            background: linear-gradient(rgba(2,6,23,0), rgba(2,6,23,.95) 35%);
        }}
        .st-key-acct_pop button {{
            width: 3rem; height: 3rem; border-radius: 50% !important;
            background: #065f46 !important; border: none !important; padding: 0;
        }}
        .st-key-acct_pop button p {{ color: #fff !important; font-weight: 800; font-size: 1.25rem; }}
        .st-key-acct_pop button svg,
        .st-key-acct_pop [data-testid="stIconMaterial"] {{ display: none; }}
        .st-key-new_chat_btn button {{
            border-radius: 999px; background: rgba(255,255,255,.95) !important;
            border: none !important; height: 3rem;
        }}
        .st-key-new_chat_btn button p {{ color: #0f172a !important; font-weight: 800; }}
        .st-key-new_chat_btn button svg,
        .st-key-new_chat_btn [data-testid="stIconMaterial"] {{
            color: #0f172a !important; fill: #0f172a !important; opacity: 1 !important;
        }}

        /* chat titles left-aligned */
        .st-key-hist_card button {{ justify-content: flex-start !important; }}
        .st-key-hist_card button [data-testid="stMarkdownContainer"] {{
            width: 100%; text-align: left !important;
        }}

        /* avatar + Nayi Chat hamesha ek hi row mein (mobile par bhi) */
        .st-key-side_bottom [data-testid="stHorizontalBlock"] {{
            flex-direction: row !important; flex-wrap: nowrap !important;
            align-items: center; gap: .6rem;
        }}
        .st-key-side_bottom [data-testid="stColumn"],
        .st-key-side_bottom [data-testid="column"] {{ min-width: 0 !important; }}
        .st-key-side_bottom [data-testid="stColumn"]:first-child,
        .st-key-side_bottom [data-testid="column"]:first-child {{
            flex: 0 0 3rem !important; width: 3rem !important;
        }}
        .st-key-side_bottom [data-testid="stColumn"]:last-child,
        .st-key-side_bottom [data-testid="column"]:last-child {{
            flex: 1 1 auto !important; width: auto !important;
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
    st.markdown(
        f'<div class="hero" style="padding-top:0"><img src="{LOGO_URI}" '
        'style="width:96px;height:96px"></div>',
        unsafe_allow_html=True,
    )
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
        {"select": "id,title,created_at", "order": "created_at.desc", "limit": "40"},
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


def shrink_image(image_bytes, mime_type="image/jpeg", max_side=1024, quality=80):
    """Photo ko chhota karo taaki upload aur AI response dono tez ho.
    Pillow na ho ya error aaye to original bytes + original mime wapas aate hain."""
    try:
        from PIL import Image

        picture = Image.open(io.BytesIO(image_bytes))
        picture = picture.convert("RGB")
        width, height = picture.size
        scale = min(1.0, max_side / max(width, height))
        if scale < 1.0:
            picture = picture.resize((int(width * scale), int(height * scale)))
        buffer = io.BytesIO()
        picture.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue(), "image/jpeg"
    except Exception:
        return image_bytes, mime_type or "image/jpeg"


def ask_gemini(history, system_prompt, temperature, image=None):
    items = [
        m for m in history[-16:]
        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
    ]
    contents = []
    for index, item in enumerate(items):
        role = "user" if item["role"] == "user" else "model"
        parts = [{"text": item["content"]}]
        is_last = index == len(items) - 1
        if image and is_last and role == "user":
            image_bytes, mime_type = image
            if len(image_bytes) > 150_000:  # 150 KB se bada ho to chhota karo
                image_bytes, mime_type = shrink_image(image_bytes, mime_type)
            parts.insert(0, {"inline_data": {
                "mime_type": mime_type or "image/jpeg",
                "data": base64.b64encode(image_bytes).decode("ascii"),
            }})
        contents.append({"role": role, "parts": parts})

    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"temperature": temperature},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"}

    last_error = None
    for attempt in range(2):  # 1 try + 1 automatic retry agar busy/timeout ho
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
        except requests.exceptions.RequestException as error:
            last_error = error
            continue
        if response.status_code in (429, 500, 503, 504) and attempt == 0:
            last_error = RuntimeError(f"HTTP {response.status_code}, dobara try kar rahi hoon...")
            continue
        try:
            data = response.json()
        except Exception:
            raise RuntimeError(f"Gemini ne unreadable response diya (HTTP {response.status_code}).")
        if not response.ok:
            raise RuntimeError(data.get("error", {}).get("message", f"HTTP {response.status_code}"))
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(
                part.get("text", "") for part in parts if not part.get("thought")
            ).strip()
            if not text:
                raise ValueError("empty")
            return text
        except (KeyError, IndexError, TypeError, ValueError):
            raise RuntimeError("Gemini ka jawab expected format mein nahi aaya.")

    raise RuntimeError(f"Gemini do baar try karne ke baad bhi busy hai: {last_error}")


def ask_ai(history, model, persona, mode, temperature, memories, image=None):
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

    if image and not GEMINI_KEY:
        raise RuntimeError("Photo samajhne ke liye GEMINI_API_KEY set karo.")

    wants_gemini = model == GEMINI_LABEL
    if wants_gemini:
        model = choose_default_model(list_models(GROQ_KEY) if GROQ_KEY else [])

    # Photo hamesha Gemini se; text mein jo model upar dropdown mein chuna wahi chalega.
    if GEMINI_KEY and (image or wants_gemini):
        try:
            return ask_gemini(history, system_prompt, temperature, image)
        except Exception as error:
            if image or not GROQ_KEY:
                raise
            st.toast(f"Gemini busy/limit: Groq se jawab de rahi hoon. ({error})")

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
        timeout=120,
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


# -------------------- Voice input (mic) --------------------
def transcribe_audio(audio_bytes):
    """Mic ki awaaz ko text mein badlo (Groq Whisper)."""
    if not GROQ_KEY:
        raise RuntimeError("Mic ke liye GROQ_API_KEY set karo.")
    response = requests.post(
        f"{GROQ_URL}/audio/transcriptions",
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        data={"model": "whisper-large-v3-turbo", "response_format": "json", "temperature": "0"},
        files={"file": ("voice.wav", audio_bytes, "audio/wav")},
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(response_error(response))
    text = (response.json().get("text") or "").strip()
    if not text:
        raise RuntimeError("Awaaz saaf sunai nahi di, dobara bolo.")
    return text


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

persona = list(PERSONAS)[0]
mode = list(MODES)[0]
temperature = MODE_TEMPERATURE[mode]
voice_on = True
accent = "Indian 🇮🇳"
slow = False

user_email = st.session_state.user.get("email", "User")
initial = (user_email[:1] or "S").upper()


def month_label(created_at):
    return (created_at or "")[:7].replace("-", "/") or "Purani chats"


def model_name(option):
    return f"✨ {GEMINI_LABEL}" if option == GEMINI_LABEL else f"⚡ {option}"


# -------------------- Sidebar: chat history + account --------------------
with st.sidebar:
    st.markdown('<div class="side-title">Chat History</div>', unsafe_allow_html=True)

    with st.container(key="hist_card"):
        chats = st.session_state.get("chats", [])
        if not chats:
            st.caption("Abhi koi chat nahi hai.")
        last_month = None
        for chat in chats:
            month = month_label(chat.get("created_at"))
            if month != last_month:
                st.markdown(f'<div class="month-label">{month}</div>', unsafe_allow_html=True)
                last_month = month
            title = chat.get("title") or "Chat"
            is_active = chat["id"] == st.session_state.get("chat_id")
            if st.button(
                title[:36],
                key=f"chat_{chat['id']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                try:
                    open_chat(chat["id"])
                except Exception as error:
                    st.error(f"Chat open nahi hui: {error}")
                st.rerun()

    with st.container(key="side_bottom"):
        account_col, new_col = st.columns([1, 4], vertical_alignment="center")

        with account_col:
            with st.container(key="acct_pop"):
                with st.popover(initial):
                    st.markdown(f"**{user_email}**")

                    if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
                        logout()
                        st.rerun()

                    if st.session_state.get("chat_id") and st.button(
                        "🗑️ Ye chat delete karo", use_container_width=True, key="del_chat_btn"
                    ):
                        try:
                            db("DELETE", "anushka_chats", {"id": f"eq.{st.session_state.chat_id}"})
                            load_chats()
                            new_chat()
                            st.rerun()
                        except Exception as error:
                            st.error(f"Chat delete nahi hui: {error}")

                    st.divider()
                    st.markdown("**🧠 Memory**")
                    st.caption("Sirf woh baatein save karo jo future chats mein yaad rakhwani hain.")
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
                        st.caption("Memory table access nahi ho paaya. SQL/table columns check karo.")

                    memories = st.session_state.get("memories", [])
                    if not memories:
                        st.caption("Abhi koi saved memory nahi hai.")
                    else:
                        for memory_item in memories:
                            st.markdown(f"• {memory_item['memory']}")
                            if st.button("Delete", key=f"delete_memory_{memory_item['id']}"):
                                try:
                                    delete_memory(memory_item["id"])
                                    st.rerun()
                                except Exception as error:
                                    st.error(f"Memory delete nahi hui: {error}")

                    st.divider()
                    st.markdown("**⚙️ Settings**")
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
                    voice_on = st.toggle("Anushka bole 🎙️", value=True)
                    accent = st.selectbox("Awaaz ka accent", list(ACCENTS))
                    slow = st.toggle("Dheere bolo", value=False)

        with new_col:
            if st.button(
                "Nayi Chat",
                icon=":material/edit_square:",
                use_container_width=True,
                key="new_chat_btn",
            ):
                new_chat()
                st.rerun()

# -------------------- Top: model picker --------------------
model_options = ([GEMINI_LABEL] if GEMINI_KEY else []) + available_models
if not model_options:
    model_options = [choose_default_model([])]
default_choice = GEMINI_LABEL if GEMINI_KEY else choose_default_model(available_models)

with st.container(key="model_bar"):
    model = st.selectbox(
        "AI Model",
        model_options,
        index=model_options.index(default_choice) if default_choice in model_options else 0,
        format_func=model_name,
        label_visibility="collapsed",
        key="top_model",
    )

# Mic: naye Streamlit mein chat box ke andar hi; purane mein upar chhota mic button.
NATIVE_MIC = "accept_audio" in inspect.signature(st.chat_input).parameters
fallback_audio = None
if not NATIVE_MIC:
    with st.popover("🎙️ Mic se bolo"):
        clip = st.audio_input("Bolo, phir stop dabao", key="mic_clip")
        if clip is not None:
            clip_bytes = clip.getvalue()
            digest = hashlib.md5(clip_bytes).hexdigest()
            if digest != st.session_state.get("last_clip"):
                st.session_state.last_clip = digest
                fallback_audio = clip_bytes

if not (GROQ_KEY or GEMINI_KEY):
    st.warning("AI key set nahi hai. Streamlit Secrets mein GROQ_API_KEY add karo.")

for message in st.session_state.get("messages", []):
    with st.chat_message(
        message["role"],
        avatar=AVATAR if message["role"] == "assistant" else None,
    ):
        st.markdown(message["content"])

if not st.session_state.get("messages"):
    st.markdown(
        f"""
        <div class="hero">
            <img src="{LOGO_URI}" alt="Anushka">
            <div class="hero-title">Namaste! Main Anushka hoon</div>
            <div class="hero-sub">All-in-one AI assistant 😼</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

chat_kwargs = {"accept_file": True, "file_type": ["png", "jpg", "jpeg", "webp"]}
if NATIVE_MIC:
    chat_kwargs["accept_audio"] = True
chat_input_value = st.chat_input("Anushka se kuch poochho... 🎮", **chat_kwargs)

st.session_state.photo_data = None
audio_bytes = fallback_audio
if chat_input_value is not None:
    prompt = (chat_input_value.text or "").strip()
    uploaded_files = chat_input_value.files
    if uploaded_files:
        uploaded_photo = uploaded_files[0]
        st.session_state.photo_data = (
            uploaded_photo.getvalue(),
            uploaded_photo.type or "image/jpeg",
        )
    native_audio = getattr(chat_input_value, "audio", None)
    if native_audio is not None:
        audio_bytes = native_audio.getvalue()
    if not prompt and uploaded_files and not audio_bytes:
        prompt = "Is photo ko dekhkar batao."
else:
    prompt = None

if audio_bytes and not prompt:
    try:
        with st.spinner("Anushka sun rahi hai... 🎙️"):
            prompt = transcribe_audio(audio_bytes)
    except Exception as error:
        st.toast(f"Awaaz text nahi ban paayi: {error}")

prompt = prompt or st.session_state.pop("pending", None)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        if st.session_state.get("photo_data"):
            st.image(st.session_state.photo_data[0], width=220)
        st.markdown(prompt)

    try:
        save_message("user", prompt)
    except Exception as error:
        st.toast(f"Chat history save nahi hui: {error}")

    with st.chat_message("assistant", avatar=AVATAR):
        success = True

        if not (GROQ_KEY or GEMINI_KEY):
            reply = "Pehle GROQ_API_KEY set karo, tab AI jawab de paayegi. 🔑"
            success = False
        else:
            try:
                spinner_text = (
                    "Anushka photo padh rahi hai... 📷"
                    if st.session_state.get("photo_data")
                    else "Anushka soch rahi hai... 🧠"
                )
                with st.spinner(spinner_text):
                    reply = ask_ai(
                        history=st.session_state.messages,
                        image=st.session_state.get("photo_data"),
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
