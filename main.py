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
    st.error("🚨 API Key Missing! Please set the GEMINI_API_KEY environment variable.")
    st.stop()

# Initialize Client
if "gemini_client" not in st.session_state:
    st.session_state.gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize Chat Session with Gemini 2.0 Flash
if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.gemini_client.chats.create(model="gemini-2.0-flash")

# --- 2. HELPER FUNCTIONS ---

def speak_text(text):
    """Converts text to speech and plays it automatically."""
    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        md = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
        st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"TTS Error: {e}")

# --- 3. UI: SIDEBAR FOR VOICE & IMAGES ---

with st.sidebar:
    st.header("🎙️ Voice & 📸 Vision")
    
    # Image Input
    uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="Image Ready")

    st.divider()
    
    # Voice Input
    st.write("Push to Speak:")
    audio_bytes = audio_recorder(
        text="",
        recording_color="#e8b62c",
        neutral_color="#6aa36f",
        icon_size="3x",
    )

# --- 4. DISPLAY CHAT HISTORY ---

for message in st.session_state.chat_session.get_history():
    role = "user" if message.role == "user" else "assistant"
    with st.chat_message(role):
        for part in message.parts:
            if part.text:
                st.markdown(part.text)
            if part.inline_data:
                st.image(part.inline_data.data)

# --- 5. PROCESSING INPUTS ---

user_text = st.chat_input("Type here or use the microphone...")

# Logic: If user records audio, Gemini processes the audio file directly!
if user_text or audio_bytes or uploaded_file:
    payload = []
    
    # 1. Add Text
    if user_text:
        payload.append(user_text)
    
    # 2. Add Audio (Gemini 2.0 Flash can 'listen' to files directly)
    if audio_bytes:
        payload.append({"mime_type": "audio/wav", "data": audio_bytes})
        if not user_text:
            payload.append("Please transcribe and respond to this voice message.")

    # 3. Add Image
    if uploaded_file:
        img_bytes = uploaded_file.getvalue()
        payload.append({"mime_type": "image/jpeg", "data": img_bytes})

    # Show User Message
    with st.chat_message("user"):
        if user_text: st.markdown(user_text)
        if audio_bytes: st.audio(audio_bytes, format="audio/wav")
        if uploaded_file: st.image(uploaded_file)

    # Generate Response
    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(payload)
            st.markdown(response.text)
            
            # Voice Output
            speak_text(response.text)
            
        except Exception as e:
            st.error(f"Gemini Error: {e}")
