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

# Use 1.5-flash to avoid daily quota limits
if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.gemini_client.chats.create(model="gemini-2.0-flash")

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
    
    # Reset Button to clear quota-heavy history
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_session = st.session_state.gemini_client.chats.create(model="gemini-2.0-flash")
        st.rerun()

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
            # 1. Handle Text
            if hasattr(part, 'text') and part.text:
                st.markdown(part.text)
            
            # 2. Handle Images (Safe Rendering)
            if hasattr(part, 'inline_data') and part.inline_data:
                if part.inline_data.data:
                    try:
                        # Streamlit is smart: it accepts both bytes and b64 strings
                        st.image(part.inline_data.data)
                    except Exception:
                        st.warning("⚠️ Could not display a previous image.")
# --- 5. INPUT HANDLING ---
user_text = st.chat_input("Type here...")

# This check ensures we only run logic if there's actually new input
if user_text or audio_bytes or uploaded_file:
    from google.genai import types 
    payload = []
    
    # 1. Handle Text Input
    if user_text:
        payload.append(types.Part.from_text(text=user_text))
    
    # 2. Handle Audio Input
    if audio_bytes:
        payload.append(types.Part.from_bytes(
            data=audio_bytes, 
            mime_type="audio/wav"
        ))
        if not user_text:
            payload.append(types.Part.from_text(text="Please respond to this voice message."))

    # 3. Handle Image Input
    if uploaded_file:
        # Check if file is larger than 10MB as a safety measure
        if uploaded_file.size > 10 * 1024 * 1024:
            st.error("File is too large! Please upload an image under 10MB.")
        else:
            payload.append(types.Part.from_bytes(
                data=uploaded_file.getvalue(), 
                mime_type="image/jpeg"
            ))

    # --- DISPLAY USER INPUT IN CHAT ---
    with st.chat_message("user"):
        if user_text: st.markdown(user_text)
        if audio_bytes: st.audio(audio_bytes)
        if uploaded_file: st.image(uploaded_file)

    # --- GET RESPONSE FROM GEMINI ---
    with st.chat_message("assistant"):
        try:
            # send_message maintains chat history automatically
            response = st.session_state.chat_session.send_message(message=payload)
            
            if response.text:
                st.markdown(response.text)
                speak_text(response.text)
            
        except Exception as e:
            st.error(f"Gemini Error: {e}")
