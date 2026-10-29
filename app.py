import base64
import io
import os
import re

import requests
import streamlit as st

st.set_page_config(page_title="Anushka SA 😼", page_icon="😼", layout="centered")

GROQ = "https://api.groq.com/openai/v1"
PREFERRED = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-20b", "openai/gpt-oss-120b"]
PERSONAS = {
    "Hinglish + Bhojpuri 😼": 'Speak in casual Hinglish with light Bhojpuri slang ("Ka ho", "Booyah pakka ba", "Tension mat lo baby 🍼").',
    "Pure Bhojpuri 🌾": "Speak in fun Bhojpuri written in Roman script, like a desi gamer.",
    "Gamer English 🎮": 'Speak in energetic gamer English with a sprinkle of "Booyah!".',
}
MODES = {
    "Gaming 🎮": "Focus on Billa Royale / Free Fire: Bermuda locations (Clock Tower, Peak, Mill), gun combos, gloo wall rushes, headshot sensitivity.",
    "Padhai 📚": "Focus on study help: explain math, science and code simply and SHORT (max ~100 words), with a tiny example when useful, and end with one practical shortcut or tip.",
    "Masti 😂": "Focus on friendly, funny, general chat.",
}
QUICK = ["🎮 Bermuda Tips", "🔥 Best Squad Setup", "🎯 Headshot Tips", "🧠 Math ka doubt hai"]
MODE_TEMP = {"Gaming 🎮": 0.9, "Padhai 📚": 0.2, "Masti 😂": 0.9}  # Padhai = kam masti, sahi jawab
ACCENTS = {"Indian 🇮🇳": "co.in", "US 🇺🇸": "com", "UK 🇬🇧": "co.uk"}


def secret(*names):
    for n in names:
        try:
            if n in st.secrets:
                return str(st.secrets[n]).strip()
        except Exception:
            pass
        if os.environ.get(n):
            return os.environ[n].strip()
    return ""


GROQ_KEY = secret("GROQ_API_KEY", "GEMINI_API_KEY")
SB_URL = secret("SUPABASE_URL").rstrip("/")
SB_KEY = secret("SUPABASE_ANON_KEY")


# ---------------- Look & feel ----------------
def style():
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bg.jpg"), "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        bg = f"linear-gradient(rgba(2,6,23,.50), rgba(2,6,23,.86)), url(data:image/jpeg;base64,{b64})"
    except Exception:
        bg = "#020617"
    st.markdown(
        f"""<style>
        .stApp {{ background: {bg}; background-size: cover; background-position: center top; background-attachment: fixed; }}
        header[data-testid="stHeader"] {{ background: transparent; }}
        [data-testid="stBottom"] > div {{ background: transparent; }}
        section[data-testid="stSidebar"] > div {{ background: rgba(2,6,23,.88); backdrop-filter: blur(8px); }}
        [data-testid="stChatMessage"] {{ background: rgba(15,23,42,.68); border-radius: 14px; }}
        div[data-testid="stForm"] {{ background: rgba(15,23,42,.72); border: 1px solid rgba(245,158,11,.28); border-radius: 16px; }}
        h1, h2, h3, label, [data-testid="stCaptionContainer"], [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li {{ color: #e2e8f0 !important; }}
        </style>""",
        unsafe_allow_html=True,
    )


style()


# ---------------- Supabase (login + chat history) ----------------
def _err(r):
    try:
        d = r.json()
        return d.get("msg") or d.get("error_description") or d.get("message") or d.get("error") or str(d)
    except Exception:
        return f"HTTP {r.status_code}"


def auth_call(path, payload, params=None):
    r = requests.post(
        f"{SB_URL}/auth/v1/{path}", params=params, json=payload,
        headers={"apikey": SB_KEY, "Content-Type": "application/json"}, timeout=30,
    )
    if not r.ok:
        raise RuntimeError(_err(r))
    return r.json()


def set_session(d):
    st.session_state.token = d["access_token"]
    st.session_state.refresh = d.get("refresh_token")
    st.session_state.user = d.get("user", {})


def logout():
    for k in ("user", "token", "refresh", "chat_id", "messages", "chats"):
        st.session_state.pop(k, None)


def db(method, table, params=None, body=None, returning=False):
    for attempt in (1, 2):
        headers = {"apikey": SB_KEY, "Authorization": f"Bearer {st.session_state.token}", "Content-Type": "application/json"}
        if returning:
            headers["Prefer"] = "return=representation"
        r = requests.request(method, f"{SB_URL}/rest/v1/{table}", params=params, json=body, headers=headers, timeout=30)
        if r.status_code == 401 and attempt == 1 and st.session_state.get("refresh"):
            try:  # token expired -> refresh once
                set_session(auth_call("token", {"refresh_token": st.session_state.refresh}, {"grant_type": "refresh_token"}))
                continue
            except Exception:
                logout()
                st.rerun()
        if not r.ok:
            raise RuntimeError(_err(r))
        return r.json() if r.text else None


def load_chats():
    st.session_state.chats = db("GET", "anushka_chats", {"select": "id,title", "order": "created_at.desc", "limit": "40"}) or []


def open_chat(cid):
    rows = db("GET", "anushka_messages", {"select": "role,content", "chat_id": f"eq.{cid}", "order": "id.asc"}) or []
    st.session_state.chat_id = cid
    st.session_state.messages = [{"role": r["role"], "content": r["content"]} for r in rows]


def new_chat():
    st.session_state.chat_id = None
    st.session_state.messages = []


def save_message(role, content):
    if st.session_state.chat_id is None:
        row = db("POST", "anushka_chats", body={"title": content[:40]}, returning=True)[0]
        st.session_state.chat_id = row["id"]
        load_chats()
    db("POST", "anushka_messages", body={"chat_id": st.session_state.chat_id, "role": role, "content": content})


def login_page():
    st.title("Anushka SA 👑")
    st.caption("BOOYAH MASTER • Login karo, apni chat history wapas pao!")
    if not (SB_URL and SB_KEY):
        st.error("Supabase set nahi hai. Secrets mein `SUPABASE_URL` aur `SUPABASE_ANON_KEY` daalo. 🔑")
        st.stop()
    t_login, t_signup = st.tabs(["Login", "Signup"])
    with t_login:
        with st.form("login"):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            go = st.form_submit_button("Login")
        if go:
            try:
                set_session(auth_call("token", {"email": email.strip(), "password": pw}, {"grant_type": "password"}))
                st.rerun()
            except Exception as e:
                st.error(f"Login nahi hua: {e}")
    with t_signup:
        with st.form("signup"):
            email2 = st.text_input("Email", key="su_email")
            pw2 = st.text_input("Password (kam se kam 6 akshar)", type="password", key="su_pw")
            pw3 = st.text_input("Password dobara", type="password", key="su_pw2")
            go2 = st.form_submit_button("Naya account banao")
        if go2:
            if pw2 != pw3:
                st.error("Dono password same nahi hain.")
            else:
                try:
                    d = auth_call("signup", {"email": email2.strip(), "password": pw2})
                    if d.get("access_token"):
                        set_session(d)
                        st.rerun()
                    else:
                        st.success("Account ban gaya! Email mein confirm link aaya hoga, usse confirm karke Login karo. ✅")
                except Exception as e:
                    st.error(f"Signup nahi hua: {e}")
    st.stop()


# ---------------- AI + voice ----------------
@st.cache_data(ttl=600, show_spinner=False)
def list_models(key):
    try:
        r = requests.get(f"{GROQ}/models", headers={"Authorization": f"Bearer {key}"}, timeout=20)
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
        "LANGUAGE RULE (most important): always reply in the same language and script as the user's latest message "
        "(Hinglish in Roman script -> Hinglish, English -> English, Hindi in Devanagari -> Hindi in Devanagari). "
        "Never switch to another language on your own. "
        f"Style flavour only (never overrides the language rule): {PERSONAS[persona]} {MODES[mode]} "
        'Keep replies punchy (under ~120 words), short lines, "•" bullets, **bold** for key terms, emojis like 😼🍼🏆🔥💥🎮.'
    )
    msgs = [{"role": "system", "content": system}] + [{"role": m["role"], "content": m["content"]} for m in history[-12:]]
    r = requests.post(
        f"{GROQ}/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": msgs, "temperature": temperature}, timeout=60,
    )
    data = r.json()
    if not r.ok:
        raise RuntimeError(data.get("error", {}).get("message", f"HTTP {r.status_code}"))
    return data["choices"][0]["message"]["content"]


@st.cache_data(show_spinner=False, max_entries=40)
def tts_bytes(text, tld, slow):
    """Real audio file -> plays in any browser (Instagram in-app browser too)."""
    from gtts import gTTS

    clean = re.sub(r"[*_`#>•]", " ", text)
    clean = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200d]", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()[:600]
    buf = io.BytesIO()
    if re.search(r"[\u0900-\u097F]", clean):
        gTTS(clean, lang="hi", slow=slow).write_to_fp(buf)
    else:
        gTTS(clean, lang="en", tld=tld, slow=slow).write_to_fp(buf)
    return buf.getvalue()


# ================= APP =================
if "user" not in st.session_state:
    login_page()

if "chats" not in st.session_state:
    new_chat()
    try:
        load_chats()
    except Exception as e:
        st.session_state.chats = []
        st.error(f"History load nahi hui. `supabase_setup.sql` chalaya? ({e})")

available = list_models(GROQ_KEY) if GROQ_KEY else []
with st.sidebar:
    st.markdown(f"**{st.session_state.user.get('email', 'User')}**")
    if st.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()
    if st.button("➕ Nayi Chat", use_container_width=True, type="primary"):
        new_chat()
        st.rerun()
    st.markdown("**Chat History 🕘**")
    for c in st.session_state.chats:
        if st.button(("💬 " + c["title"]) if c["title"] else "💬 Chat", key=f"c_{c['id']}", use_container_width=True,
                     type="primary" if c["id"] == st.session_state.chat_id else "secondary"):
            try:
                open_chat(c["id"])
            except Exception as e:
                st.error(str(e))
            st.rerun()
    if st.session_state.chat_id and st.button("🗑️ Ye chat delete karo", use_container_width=True):
        try:
            db("DELETE", "anushka_chats", {"id": f"eq.{st.session_state.chat_id}"})
            load_chats()
        except Exception as e:
            st.error(str(e))
        new_chat()
        st.rerun()
    with st.expander("⚙️ Settings"):
        persona = st.selectbox("Persona Style", list(PERSONAS))
        mode = st.radio("Mode", list(MODES))
        temperature = st.slider("Masti level 🔥", 0.0, 1.5, MODE_TEMP[mode], 0.1, key=f"temp_{mode}")
        opts = available or [default_model(available)]
        dm = default_model(available)
        model = st.selectbox("AI Model", opts, index=opts.index(dm) if dm in opts else 0)
        voice_on = st.toggle("Anushka bole 🎙️", value=True)
        accent = st.selectbox("Awaaz ka accent", list(ACCENTS))
        slow = st.toggle("Dheere bolo", value=False)

st.title("Anushka SA 👑")
st.caption("BOOYAH MASTER • Gaming, padhai aur masti — sab poochho!")
if not GROQ_KEY:
    st.warning("AI key set nahi hai. Secrets mein `GROQ_API_KEY` daalo. 🔑")

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
    try:
        save_message("user", prompt)
    except Exception as e:
        st.toast(f"History save nahi hui: {e}")
    with st.chat_message("assistant", avatar="😼"):
        ok = True
        if not GROQ_KEY:
            reply, ok = "Pehle AI key daalo, tab hum baat karenge! 🔑😼", False
        else:
            try:
                with st.spinner("Anushka likh rahi hai..."):
                    reply = ask_ai(st.session_state.messages, model, persona, mode, temperature)
            except Exception as e:
                reply, ok = f"Arey, network ne hag diya! 😼💥\n\n`{e}`", False
        st.markdown(reply)
        if ok and voice_on:
            try:
                st.audio(tts_bytes(reply, ACCENTS[accent], slow), format="audio/mp3", autoplay=True)
            except Exception:
                st.caption("🔇 Awaaz abhi nahi ban payi.")
    st.session_state.messages.append({"role": "assistant", "content": reply})
    if ok:
        try:
            save_message("assistant", reply)
        except Exception as e:
            st.toast(f"History save nahi hui: {e}")
                  
