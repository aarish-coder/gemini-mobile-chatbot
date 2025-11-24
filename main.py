import streamlit as st
import os
from google import genai
from google.genai.errors import APIError

# --- 1. CONFIGURATION AND INITIALIZATION ---

st.title("🤖 Spark: Your Friendly AI Assistant")

# Retrieve the API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    # Stop execution if the key is missing
    st.error("🚨 **API Key Missing!** 🚨\nPlease set the `GEMINI_API_KEY` environment variable in your terminal before running the app.")
    st.stop()

# Initialize Gemini client and store in session_state
if "gemini_client" not in st.session_state:
    try:
        st.session_state.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"Error initializing Gemini client: {e}")
        st.stop()

# Create chat session only once, using the fast and efficient gemini-2.5-flash model
if "chat_session" not in st.session_state:
    try:
        st.session_state.chat_session = st.session_state.gemini_client.chats.create(model="gemini-2.5-flash")
    except Exception as e:
        st.error(f"Error creating chat session: {e}")
        st.stop()


# --- 2. DISPLAY CHAT HISTORY ---

# Iterate through the history of the chat session to display previous messages
for message in st.session_state.chat_session.get_history():
    # Map the Gemini 'user' and 'model' roles to Streamlit 'user' and 'assistant' roles
    role = "user" if message.role == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 3. HANDLE NEW USER INPUT ---

user_prompt = st.chat_input("Say something to Spark...")

if user_prompt:
    # Display the user's prompt immediately
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Prepare to display the assistant's response
    with st.chat_message("assistant"):
        try:
            response_stream = st.session_state.chat_session.send_message_stream(user_prompt)
            st.write_stream(stream_text_generator(response_stream))
        except APIError as e:
            # Handle specific API errors gracefully
            if "400" in str(e) and "API key not valid" in str(e):
                st.error("🔑 **Authentication Error** 🔑\n\nYour API key appears to be invalid. Please check your `GEMINI_API_KEY` environment variable.")
            elif "503 UNAVAILABLE" in str(e):
                st.error("⚠️ **Model Overload Error** ⚠️\n\nThe AI model is temporarily overloaded. Please wait a moment and try your query again.")
            else:
                st.error(f"An unexpected API error occurred: {e}")
                
        except Exception as e:
            # Handle general Python exceptions
            st.error(f"An unexpected error occurred: {e}")
