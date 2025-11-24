import streamlit as st
import requests
import time
import os
import json
from datetime import datetime

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
        st.error("Login failed.")

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
            <h2 class='accent'>MAN Sales Chatbot 🔐</h2>
            <p class='muted'>Please log in to continue</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🔓 Login with MAN SSO"):
            auth.redirect_to_login()

    st.stop()

# ============================================
# SIDEBAR
# ============================================
st.sidebar.write(f"👋 Logged in as {st.session_state.username}")

if st.sidebar.button("Logout"):
    auth.logout()
    st.stop()

# Sidebar Logo
img_path = os.path.join(os.path.dirname(__file__), "logo.png")
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
st.sidebar.image(img_path, use_container_width=True)

# ============================================
# CHATBOT UI
# ============================================
st.markdown("<h1 class='accent center'>💬 Sales Argumentation</h1>", unsafe_allow_html=True)

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
        "Hello there 👋! I'm your MAN Sales Assistant.\n\n"
        "I can help you explore MAN vehicle features, performance specs, and sales arguments."
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
    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("Is the information correct and useful?")
        correctness = st.slider(
            0, 5,
            key="fb_correct",
            value=st.session_state.fb_correct
        )
        st.markdown("<div style='display:flex; justify-content:space-between; font-size:12px;'><span>Not correct</span><span>Correct</span></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("Did the answer cover everything you wanted to know?")
        coverage = st.slider(
            0, 5,
            key="fb_coverage",
            value=st.session_state.fb_coverage
        )
        st.markdown("<div style='display:flex; justify-content:space-between; font-size:12px;'><span>No</span><span>Yes</span></div>", unsafe_allow_html=True)

    with col_right:
        notes_correct = st.text_area(
            "Write additional feedback here (e.g. what was incorrect?)",
            key="fb_notes_correct",
            value=st.session_state.fb_notes_correct,
            height=70
        )
        notes_coverage = st.text_area(
            "Write additional feedback here (e.g. what is missing?)",
            key="fb_notes_coverage",
            value=st.session_state.fb_notes_coverage,
            height=70
        )

        if st.button("Submit feedback"):
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
            st.success("Thank you for your feedback!")
            st.session_state.awaiting_feedback = False
            st.rerun()

# ============================================
# SUGGESTED QUESTIONS
# ============================================
if st.session_state.get("show_suggestions", False):
    st.markdown("<p class='muted center'>Try asking:</p>", unsafe_allow_html=True)

    suggestions = [
        "What can you tell me about the offroad anti-lock ABS?",
        "How does MAN's fuel efficiency compare to competitors?",
        "What are the key safety features of the TGX model?"
    ]

    cols = st.columns(len(suggestions))

    for i, q in enumerate(suggestions):
        with cols[i]:
            if st.button(q, key=f"sugg{i}"):
                st.session_state.messages.append({"role": "user", "content": q})
                with st.spinner("Thinking..."):
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
if prompt := st.chat_input("Type your message here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Thinking..."):
        answer = query_api(prompt)

    st.session_state.messages.append({"role": "assistant", "content": answer})

    st.session_state.last_user_prompt = prompt
    st.session_state.last_assistant_answer = answer
    st.session_state.awaiting_feedback = True
    st.session_state.show_suggestions = False

    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)