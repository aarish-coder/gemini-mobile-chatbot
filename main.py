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
    st.session_state.chat_session = st.session_state.gemini_client.chats.create(model="gemini-2.5-flash")

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
        st.session_state.chat_session = st.session_state.gemini_client.chats.create(model="gemini-2.5-flash")
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
            
            # 2. Handle Images (Inline Data)
            if hasattr(part, 'inline_data') and part.inline_data:
                try:
                    # Streamlit can handle the raw bytes directly from part.inline_data.data
                    st.image(part.inline_data.data)
                except Exception as e:
                    st.error(f"Error displaying history image: {e}")
                    
# --- 5. INPUT HANDLING ---
user_text = st.chat_input("Type here...")

if user_text or audio_bytes or uploaded_file:
    # Use types.Part to wrap multimodal data properly
    from google.genai import types 
    payload = []
    
    # Text Input
    if user_text:
        payload.append(types.Part.from_text(text=user_text))
    
    # Audio Input
    if audio_bytes:
        payload.append(types.Part.from_bytes(
            data=audio_bytes, 
            mime_type="audio/wav"
        ))
        # If no text was typed, give the model a hint
        if not user_text:
            payload.append(types.Part.from_text(text="Please respond to this voice message."))

    # Image Input
    if uploaded_file:
        payload.append(types.Part.from_bytes(
            data=uploaded_file.getvalue(), 
            mime_type="image/jpeg"
        ))

    # Display User Input in Chat UI
    with st.chat_message("user"):
        if user_text: st.markdown(user_text)
        if audio_bytes: st.audio(audio_bytes)
        if uploaded_file: st.image(uploaded_file)

    # Get Response
    with st.chat_message("assistant"):
        try:
            # Now payload is a list of Part objects, which Gemini 2.5/SDK expects
            response = st.session_state.chat_session.send_message(message=payload)
            st.markdown(response.text)
            speak_text(response.text)
        except Exception as e:
            st.error(f"Gemini Error: {e}")
