import streamlit as st
import requests
import time
import os
import json
from datetime import datetime

import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Sales Argumentation",  page_icon="logo.png", layout="wide")




# st.set_option('deprecation.showfileUploaderEncoding', False)

# st.set_option('deprecation.showPyplotGlobalUse', False)

# Import Hosted UI Auth helper
from auth_streamlit import Auth

# ============================================
# INITIALIZE AUTH HANDLER
# ============================================
auth = Auth()

# ============================================
# LOAD CSS
# ============================================
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")

# ============================================
# AUTHENTICATION STATE
# ============================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user" not in st.session_state:
    st.session_state.user = None

# ============================================
# CAPTURE COGNITO CALLBACK (?code=)
# ============================================
query_params = st.experimental_get_query_params()

if "code" in query_params and not st.session_state.authenticated:
    code = query_params["code"][0]

    user_info = auth.handle_callback(code)

    if user_info:
        st.session_state.user = user_info
        st.session_state.authenticated = True
        st.session_state.username = user_info.get("email", "Unknown User")
    else:
        st.error("Anmeldung fehlgeschlagen.")

# ============================================
# FEEDBACK STATE
# ============================================
for key, default in {
    "awaiting_feedback": False,
    "last_user_prompt": "",
    "last_assistant_answer": "",
    "fb_correct": 0,
    "fb_coverage": 0,
    "fb_notes_correct": "",
    "fb_notes_coverage": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================
# SAVE FEEDBACK
# ============================================
def save_feedback(entry):
    file_path = "feedback.json"
    data = []

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except:
                data = []

    data.append(entry)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ============================================
# LOGIN PAGE (Hosted UI Login)
# ============================================
if not st.session_state.authenticated:
    st.markdown("""
        <div class="login-card">
            <h2 class='accent'>	MAN Sales Argumentation Chatbot 🔐</h2>
            <p class='muted'> Bitte melden Sie sich an, um fortzufahren. </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🔓 Anmeldung mit MAN SSO"):
            auth.redirect_to_login()

    st.stop()
# st.session_state.username="Jessi" #TODO
# ============================================
# SIDEBAR
# ============================================


# Sidebar Logo
img_path = os.path.join(os.path.dirname(__file__), "logo.png")
# st.sidebar.markdown("<br><br>", unsafe_allow_html=True)

# Custom CSS to remove top padding
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            padding-top: 0rem;
        }
    </style>
""", unsafe_allow_html=True)

# st.sidebar.image(img_path, use_container_width=True) TODO
st.sidebar.image(img_path)

st.sidebar.write(f"👋 Angemeldet als {st.session_state.username}")

if st.sidebar.button("Abmelden"):
    auth.logout()
    st.stop()

# ============================================
# CHATBOT UI
# ============================================
st.markdown("<h1 class='accent center'>💬 MAN Sales Argumentation Chatbot</h1>", unsafe_allow_html=True)

def query_api(prompt: str) -> str:
    url = "https://teqmr90em4.execute-api.eu-west-1.amazonaws.com/test/prompt"
    payload = {"prompt": prompt}
    headers = {
        "Content-Type": "application/json",
        "authorizationToken": "testStreamlit"
    }

    try:
        response = requests.get(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("body", "No response from API.")
    except Exception as e:
        print("API error:", e)
        return "Error contacting API."

# Chat Container
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Initial Assistant Message
if not st.session_state.get("welcome_shown", False):
    welcome_text = (
        "Hallo! Ich bin Ihr MAN Sales-Assistent.\n\n"
	    "Ich unterstütze Sie dabei, die Fahrzeugmerkmale und Verkaufsargumente von MAN einfach und übersichtlich zu entdecken."

    )
    st.session_state.messages.append({"role": "assistant", "content": welcome_text})
    st.session_state.welcome_shown = True
    st.session_state.show_suggestions = True

# Display Messages
st.markdown("<div class='message-area'>", unsafe_allow_html=True)
for message in st.session_state.messages:
    role_class = "user" if message["role"] == "user" else "assistant"
    st.markdown(
        f"<div class='chat-bubble {role_class}'>{message['content']}</div><div class='clear'></div>",
        unsafe_allow_html=True
    )
st.markdown("</div>", unsafe_allow_html=True)

# ============================================
# FEEDBACK UI BELOW THE LAST ANSWER
# ============================================
# st.session_state.awaiting_feedback=True #TODO
if st.session_state.awaiting_feedback:
    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("Sind die Informationen korrekt?")
        correctness = st.slider(
            label="",  # remove duplicated label
            min_value=0,
            max_value=5,
            value=st.session_state.fb_correct,
            key="fb_correct"
        )
        st.markdown(
            "<div style='display:flex; justify-content:space-between; font-size:12px;'>"
            "<span>Nicht korrekt</span><span>Korrekt</span></div>",
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("Deckt die Antwort alles ab, was gewünscht war?")
        coverage = st.slider(
            label="",  # remove duplicated label
            min_value=0,
            max_value=5,
            value=st.session_state.fb_coverage,
            key="fb_coverage"
        )
        st.markdown(
            "<div style='display:flex; justify-content:space-between; font-size:12px;'>"
            "<span>Nicht vollständig</span><span>Vollständig</span></div>",
            unsafe_allow_html=True
        )

    with col_right:
        notes_correct = st.text_area(
            "Bitte geben Sie zusätzliches Feedback ein (z.B. Was war nicht korrekt?)",
            key="fb_notes_correct",
            value=st.session_state.fb_notes_correct,
            height=70
        )
        notes_coverage = st.text_area(
            "Bitte geben Sie zusätzliches Feedback ein (z.B. Was hat gefehlt?).",
            key="fb_notes_coverage",
            value=st.session_state.fb_notes_coverage,
            height=70
        )

    if st.button("Feedback versenden"):
        entry = {
            "username": st.session_state.username,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_prompt": st.session_state.last_user_prompt,
            "assistant_answer": st.session_state.last_assistant_answer,
            "correctness_score": correctness,
            "correctness_notes": notes_correct,
            "coverage_score": coverage,
            "coverage_notes": notes_coverage,
        }
        save_feedback(entry)
        st.success("Ihr Feedback wurde erfolgreich versendet!")
        st.session_state.awaiting_feedback = False
        st.rerun()

# ============================================
# SUGGESTED QUESTIONS
# ============================================
if st.session_state.get("show_suggestions", False):
    st.markdown("<p class='muted center'>Prompt-Vorschläge:</p>", unsafe_allow_html=True)

    suggestions = [
     "Was können Sie mir über das Offroad-Antiblockiersystem ABS sagen?",
    "Wie schneidet MAN im Vergleich zu Wettbewerbern in Sachen Kraftstoffeffizienz ab?",
    "Was sind die wichtigsten Sicherheitsmerkmale des TGX-Modells?"
    ]

    cols = st.columns(len(suggestions))

    for i, q in enumerate(suggestions):
        with cols[i]:
            if st.button(q, key=f"sugg{i}"):
                st.session_state.messages.append({"role": "user", "content": q})
                with st.spinner("Die Antwort wird generiert..."):
                    answer = query_api(q)
                st.session_state.messages.append({"role": "assistant", "content": answer})

                st.session_state.last_user_prompt = q
                st.session_state.last_assistant_answer = answer
                st.session_state.awaiting_feedback = True
                st.session_state.show_suggestions = False
                st.rerun()

# ============================================
# USER CHAT INPUT
# ============================================
if prompt := st.chat_input("Geben Sie Ihre Nachricht hier ein."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Die Antwort wird generiert..."):
        answer = query_api(prompt)

    st.session_state.messages.append({"role": "assistant", "content": answer})

    st.session_state.last_user_prompt = prompt
    st.session_state.last_assistant_answer = answer
    st.session_state.awaiting_feedback = True
    st.session_state.show_suggestions = False

    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)