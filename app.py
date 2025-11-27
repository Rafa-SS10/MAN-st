import streamlit as st
import streamlit.components.v1 as components
import requests
import time
import os
import json
import urllib.parse
from datetime import datetime
from feedback_storage import save_feedback

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

st.set_page_config(page_title="Sales Argumentation", page_icon="logo.png", layout="wide")

# Import Hosted UI Auth helper
from auth_streamlit import Auth

# ============================================
# INITIALIZE AUTH HANDLER
# ============================================
auth = Auth()

# ============================================
# SAFE SESSION_STATE INITIALIZATION (top of file)
# ============================================
# Inicializa todas as chaves usadas no app para evitar AttributeError
INITIAL_SESSION_KEYS = {
    "authenticated": False,
    "user": None,
    "username": "Guest",
    "redirect": False,
    "awaiting_feedback": False,
    "last_user_prompt": "",
    "last_assistant_answer": "",
    "fb_correct": 0,
    "fb_coverage": 0,
    "fb_relevance": 0,
    "fb_notes_correct": "",
    "fb_notes_coverage": "",
    "fb_notes_relevance": "",
    "messages": [],
    "welcome_shown": False,
    "show_suggestions": False,
}

for k, v in INITIAL_SESSION_KEYS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================
# LOAD CSS
# ============================================
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")

# ============================================
# HELPER: Robust redirect function (uses Auth if available)
# ============================================
def perform_redirect_via_components():
    """
    Tenta usar auth.redirect_to_login() se existir.
    Caso contrário, tenta construir a URL a partir de atributos comuns do objeto auth
    e executar o redirecionamento via components.html (garante execução imediata).
    """
    # Primeiro, se Auth fornece um method redirect_to_login, use-o (assume que faz components.html internamente).
    if hasattr(auth, "redirect_to_login"):
        try:
            auth.redirect_to_login()
            return
        except Exception:
            # fallback para construir URL localmente
            pass

    # Fallback: tente construir a URL a partir de atributos esperados
    authorization = getattr(auth, "authorization", None)
    client_id = getattr(auth, "client_id", None)
    redirect_uri = getattr(auth, "redirect_uri", None)

    if not (authorization and client_id and redirect_uri):
        # Não conseguimos construir a URL: log e exiba erro
        st.error("Unable to redirect: missing auth configuration. Check your Auth class.")
        return

    login_url = (
        f"{authorization}"
        f"?response_type=code"
        f"&client_id={urllib.parse.quote(client_id)}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
        f"&scope=openid+email+profile"
    )

    # Executa redirecionamento do navegador (componente garante execução imediata)
    components.html(f"""
        <script>
            window.location.href = "{login_url}";
        </script>
    """, height=0)

# ============================================
# CAPTURE COGNITO CALLBACK (?code=)
# ============================================
query_params = st.query_params
# Debug: (remova em produção)
# st.write("Query Params:", query_params)

if "code" in query_params and not st.session_state.authenticated:
    code = query_params["code"][0]
    try:
        user_info = auth.handle_callback(code)
    except Exception as e:
        user_info = None
        st.error("Fehler beim Verarbeiten des Callbacks.")
        print("handle_callback error:", e)

    if user_info:
        st.session_state.user = user_info
        st.session_state.authenticated = True
        st.session_state.username = user_info.get("email", st.session_state.get("username", "User"))
        # Opcional: limpar o code para não processar de novo (não redirecionamos aqui, apenas limpamos)
        try:
            st.query_params = {}
        except Exception:
            # Se por algum motivo isso falhar, não interrompe o fluxo.
            pass
    else:
        st.error("Anmeldung fehlgeschlagen.")

# ============================================
# LOGIN PAGE (Hosted UI Login)
# ============================================
if not st.session_state.get("authenticated", False):
    st.markdown("""
        <div class="login-card">
            <h2 class='accent'> MAN Sales Argumentation Chatbot 🔐</h2>
            <p class='muted'> Bitte melden Sie sich an, um fortzufahren. </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🔓 Anmeldung mit MAN SSO"):
            # Sinaliza intenção de redirect — será processada abaixo
            st.session_state.redirect = True

    # Se a flag está ativa, faz o redirecionamento via JS (componente)
    if st.session_state.redirect:
        perform_redirect_via_components()
        # NÃO definimos st.query_params = {} aqui — evitar mexer na URL antes do JS executar.
        # Após disparar o redirect, podemos resetar a flag (opcional, mas não necessário)
        # Se o componente já navegou, a execução do Streamlit interrompe aqui.
        # Mantemos st.stop para garantir que nada mais seja mostrado localmente.
        st.stop()

    st.stop()

# ============================================
# SIDEBAR
# ============================================
img_path = os.path.join(os.path.dirname(__file__), "logo.png")
st.sidebar.image(img_path)
st.sidebar.write(f"👋 Angemeldet als {st.session_state.username}")

if st.sidebar.button("Abmelden"):
    # Se a sua Auth tem method logout, usamos, caso contrário exiba mensagem
    if hasattr(auth, "logout"):
        try:
            auth.logout()
        except Exception as e:
            print("Logout error:", e)
    # limpa estado local
    for key in ["authenticated", "user", "username"]:
        st.session_state[key] = INITIAL_SESSION_KEYS.get(key)
    st.experimental_rerun()

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

if "messages" not in st.session_state or not st.session_state.messages:
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

        relevance = st.slider(
            label="Sind die Informationen hilfreich für die Frage?",
            min_value=0,
            max_value=5,
            value=st.session_state.fb_relevance,
            key="fb_relevance"
        )
        st.markdown(
            "<div style='display:flex; justify-content:space-between; font-size:12px;'>"
            "<span>Nicht hilfreich</span><span>Hilfreich</span></div>",
            unsafe_allow_html=True
        )

    with col_right:
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
        notes_relevance = st.text_area(
            "Bitte geben Sie zusätzliches Feedback ein (z.B. Warum war es nicht hilfreich?).",
            key="fb_notes_relevance",
            value=st.session_state.fb_notes_relevance,
            height=70
        )

    col_left1, col_right1 = st.columns([2, 1])
    with col_right1:
        st.markdown("<div class='thin-button'>", unsafe_allow_html=True)
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
                "relevance_score": relevance,
                "relevance_notes": notes_relevance,  # FIX: was wrong in original
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