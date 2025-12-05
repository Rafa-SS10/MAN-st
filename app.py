import streamlit as st
import requests
import time
import os
import json
from datetime import datetime
from feedback_storage import save_feedback
from conversation_storage import save_conversation

import hashlib
import uuid

import os
os.environ["STREAMLIT_SUPPRESS_DEPRECATION_WARNINGS"] = "true"


import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
st._show_deprecation_warning = lambda *args, **kwargs: None
st.set_page_config(page_title="Sales Argumentation",  page_icon="logo.png", layout="wide")


warnings.filterwarnings(
    "ignore",
    message="Please replace st.experimental_get_query_params with st.query_params"
)

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

# st.session_state.authenticated = True # TODO
# st.session_state.username="Testuser" # TODO
# st.session_state.user_id = hashlib.sha256(st.session_state.username.encode()).hexdigest()[:8]  # TODO
# if "session_id" not in st.session_state:
#     st.session_state.session_id = str(uuid.uuid4())  # Generate a unique ID # TODO
# st.session_state.awaiting_feedback= True # TODO
    
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
        st.session_state.user_id = hashlib.sha256(st.session_state.username.encode()).hexdigest()[:8]  # 8-char ID
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())  # Generate a unique ID

        
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
    "fb_relevance": 0,
    "fb_notes_correct": "",
    "fb_notes_coverage": "",
    "fb_notes_relevance": "",
    "history": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

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
# ============================================
# SIDEBAR
# ============================================


# Logo-Pfad
img_path = os.path.join(os.path.dirname(__file__), "logo.png")

# CSS für Sidebar-Layout
st.markdown("""
    <style>
        /* Entfernt Standard-Padding oben */
        [data-testid="stSidebar"] {
            padding-top: 0rem;
        }

        /* Logo ohne Schatten */
        [data-testid="stSidebar"] img {
            box-shadow: none !important;
        }

        /* Sidebar als Flexbox für dynamische Anordnung */
        [data-testid="stSidebar"] > div:first-child {
            display: flex;
            flex-direction: column;
            justify-content: flex-start; /* Alles oben */
            height: 100vh;
        }
    </style>
""", unsafe_allow_html=True)

# Logo ganz oben
st.sidebar.image(img_path)

# Benutzerinfo direkt unter dem Logo
st.sidebar.write(f"👋 Angemeldet als {st.session_state.username}")


# Logout
if st.sidebar.button("Abmelden"):
    auth.logout()
    st.stop()

st.sidebar.markdown(
    """
    <style>
        [data-testid="stSidebar"] > div:first-child {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100vh;
        }
        .sidebar-footer {
            text-align: left;
            font-size: 13px;
            padding: 10px 0;
        }
    </style>
    """,
    unsafe_allow_html=True
)



# Footer-Hinweis unten
st.sidebar.markdown(
    """
    <div class="sidebar-footer">
        KI-generierte Inhalte können fehlerhaft sein.<br>
        Bitte überprüfen Sie wichtige Informationen.
    </div>
    """,
    unsafe_allow_html=True
)




# ============================================
# CHATBOT UI
# ============================================
st.markdown("<h1 class='accent center'Ftod>💬 MAN Sales Argumentation Chatbot</h1>", unsafe_allow_html=True)

def query_api(prompt: str, history) -> str:
    url = "https://an4zcmir30.execute-api.eu-west-1.amazonaws.com/dev/v1"
    payload = {"prompt": prompt, "history": history}
    headers = {
        "Content-Type": "application/json",
        "authorizationToken": "testStreamlit"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("body", "No response from API.")
    except Exception as e:
        print("API error:", e)
        return "Error contacting API."

# Chat Container
# st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

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

if st.session_state.awaiting_feedback:
    st.markdown("<h2 style='font-size:18px;'>Geben Sie uns Feedback</h2>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("Korrektheit:")

        correctness = st.slider(
            label="Sind die Informationen korrekt?",
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
        st.markdown("Vollständigkeit:")
        coverage = st.slider(
            label="Deckt die Antwort alles ab, was gewünscht war?",
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

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("Ton & Stil:")
        tone_style = st.slider(
            label="Ist die Antwort professionell, sachlich und unterstützend?",
            min_value=0,
            max_value=5,
            value=st.session_state.get("fb_tone_style", 0),
            key="fb_tone_style"
        )
        st.markdown(
            "<div style='display:flex; justify-content:space-between; font-size:12px;'>"
            "<span>nicht passend</span><span>passend</span></div>",
            unsafe_allow_html=True
        )

    with col_right:
        st.markdown("<div class='right-column'>", unsafe_allow_html=True)
        notes_correct = st.text_area(
            "Bitte geben Sie zusätzliches Feedback ein (z.B. Was war nicht korrekt?).",
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
        notes_tone_style = st.text_area(
            "Bitte geben Sie zusätzliches Feedback ein (z.B. Wie kann die Antwort verständlicher und lösungsorientierter gestaltet werden?)",
            key="fb_notes_tone_style",
            value=st.session_state.get("fb_notes_tone_style", ""),
            height=70
        )

    col_left1, col_right1 = st.columns([2, 1])
    with col_right1:
        st.markdown("<div class='thin-button'>", unsafe_allow_html=True)
        if st.button("Feedback versenden"):
            entry = {
                "username": st.session_state.username,
                "userId": st.session_state.user_id,
                "sessionId": st.session_state.session_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user_prompt": st.session_state.last_user_prompt,
                "assistant_answer": st.session_state.last_assistant_answer,
                "correctness_score": correctness,
                "correctness_notes": notes_correct,
                "coverage_score": coverage,
                "coverage_notes": notes_coverage,
                "tone_style_score": tone_style,
                "tone_style_notes": notes_tone_style
            }
            save_feedback(entry)
            st.success("Ihr Feedback wurde erfolgreich versendet!")
            time.sleep(2)
            st.session_state.awaiting_feedback = False
            st.rerun()

# ============================================
# SUGGESTED QUESTIONS
# ============================================
if st.session_state.get("show_suggestions", False):
    st.markdown("Prompt-Vorschläge:", unsafe_allow_html=True)

    suggestions = [
        "Wie funktioniert die OptiView-Umschaltung?",
        "Welche Funktionen bietet die kabelgebundene Fernbedienung im Ruhebereich?",
        "Kann der Fahrer während der Fahrt die Klimaanlage manuell regeln?"
    ]

    cols = st.columns(len(suggestions))

    for i, q in enumerate(suggestions):
        with cols[i]:
            if st.button(q, key=f"sugg{i}"):
                # Add user message
                st.session_state.messages.append({"role": "user", "content": q})

                # Get assistant response
                with st.spinner("Die Antwort wird generiert..."):
                    answer = query_api(q, st.session_state.history)

                # Add assistant message
                st.session_state.messages.append({"role": "assistant", "content": answer})

                # Update session state
                st.session_state.last_user_prompt = q
                st.session_state.last_assistant_answer = answer
                st.session_state.awaiting_feedback = True
                st.session_state.show_suggestions = False
                st.session_state.history.append((q, answer))

                # ✅ Save conversation to S3
                from conversation_storage import save_conversation
                from datetime import datetime

                conversation_entry = {
                    "username": st.session_state.username,
                    "userId": st.session_state.user_id,
                    "sessionId": st.session_state.session_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "question": q,
                    "answer": answer
                }
                save_conversation(conversation_entry)
                

                # Refresh UI
                st.rerun()

# ============================================
# USER CHAT INPUT
# ============================================
if prompt := st.chat_input("Geben Sie Ihre Nachricht hier ein."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get assistant response
    with st.spinner("Die Antwort wird generiert..."):
        
        answer = query_api(prompt, st.session_state.history)

    # Add assistant message
    st.session_state.messages.append({"role": "assistant", "content": answer})
    # st.session_state.messages.append({"role": "assistant", "content": st.session_state.history}) #TODO

    # Update session state
    st.session_state.last_user_prompt = prompt
    st.session_state.last_assistant_answer = answer
    st.session_state.awaiting_feedback = True
    st.session_state.show_suggestions = False
    st.session_state.history.append((prompt, answer))


    # ✅ Save conversation to S3
    from conversation_storage import save_conversation
    from datetime import datetime

    conversation_entry = {
        "username": st.session_state.username,
        "userId": st.session_state.user_id,
        "sessionId": st.session_state.session_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": prompt,
        "answer": answer
    }
    save_conversation(conversation_entry)
    

    # Refresh UI
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)