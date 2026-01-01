import streamlit as st
import os
import io
import base64
from google import genai
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Spark AI", page_icon="🤖")
st.title("🤖 Spark: Voice & Vision AI")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error("🚨 API Key Missing! Set it in Streamlit Secrets.")
    st.stop()

if "gemini_client" not in st.session_state:
    st.session_state.gemini_client = genai.Client(api_key=GEMINI_API_KEY)

if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.gemini_client.chats.create(model="gemini-1.5-flash")

# --- 2. VOICE OUTPUT ---
def speak_text(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        md = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
        st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"TTS Error: {e}")

# --- 3. UI SIDEBAR ---
with st.sidebar:
    st.header("🎙️ Voice & 📸 Vision")
    uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="Image Ready")
    
    st.divider()
    st.write("Push to Speak:")
    audio_bytes = audio_recorder(text="", icon_size="3x")

# --- 4. CHAT HISTORY ---
for message in st.session_state.chat_session.get_history():
    role = "user" if message.role == "user" else "assistant"
    with st.chat_message(role):
        for part in message.parts:
            if part.text:
                st.markdown(part.text)
            if part.inline_data:
                st.image(part.inline_data.data)

# --- 5. INPUT HANDLING ---
user_text = st.chat_input("Type here...")

if user_text or audio_bytes or uploaded_file:
    payload = []
    
    # Text Input
    if user_text:
        payload.append(user_text)
    
    # Audio Input
    if audio_bytes:
        payload.append({"mime_type": "audio/wav", "data": audio_bytes})
        if not user_text:
            payload.append("Please respond to this voice message.")

    # Image Input
    if uploaded_file:
        payload.append({"mime_type": "image/jpeg", "data": uploaded_file.getvalue()})

    # Display User Input
    with st.chat_message("user"):
        if user_text: st.markdown(user_text)
        if audio_bytes: st.audio(audio_bytes)
        if uploaded_file: st.image(uploaded_file)

    # Get Response
    with st.chat_message("assistant"):
        try:
            # We use send_message here to avoid the 'list' error with streaming
            response = st.session_state.chat_session.send_message(message=payload)
            st.markdown(response.text)
            speak_text(response.text)
        except Exception as e:
            st.error(f"Gemini Error: {e}")
