import streamlit as st
from helpers import (
    get_next_api_key, 
    get_groq_client, 
    get_assistant_response, 
    create_patient_intake_form,
    get_diagnostic_analysis, 
    create_medical_report, 
    get_medical_assistant_response, 
    check_medical_alerts, 
    convert_md_to_html, 
    strip_before_marker, 
    generate_pdf_report, 
    get_special_response, 
    send_feedback_email,
    process_stream_with_format_enforcement,
    API_KEYS
)
import uuid
from datetime import datetime
from streamlit_option_menu import option_menu

# Add key rotation counter to session state
if "api_key_index" not in st.session_state:
    st.session_state.api_key_index = 0

# Initialize conversation management session states
if "conversations" not in st.session_state:
    st.session_state.conversations = {}
if "current_conversation_id" not in st.session_state:
    new_id = str(uuid.uuid4())
    st.session_state.conversations[new_id] = {
        "chat_history": [],
        "created_at": datetime.now().strftime("%b %d, %I:%M %p"),
        "title": "New Conversation"
    }
    st.session_state.current_conversation_id = new_id

# Initialize patient data session states
if "patient_records" not in st.session_state:
    st.session_state.patient_records = []
if "patient_analyses" not in st.session_state:
    st.session_state.patient_analyses = {}

def create_new_conversation():
    """Create a new conversation and set it as current"""
    new_id = str(uuid.uuid4())
    st.session_state.conversations[new_id] = {
        "chat_history": [],
        "created_at": datetime.now().strftime("%b %d, %I:%M %p"),
        "title": "New Conversation"
    }
    st.session_state.current_conversation_id = new_id

def set_current_conversation(conversation_id):
    """Set the current conversation to the selected one"""
    st.session_state.current_conversation_id = conversation_id

def delete_conversation(conversation_id):
    """Delete a conversation"""
    if conversation_id in st.session_state.conversations:
        # If deleting current conversation, switch to another one first
        if conversation_id == st.session_state.current_conversation_id:
            # Find another conversation to switch to
            remaining_ids = [cid for cid in st.session_state.conversations.keys() if cid != conversation_id]
            if remaining_ids:
                st.session_state.current_conversation_id = remaining_ids[0]
            else:
                # Create a new conversation if we're deleting the last one
                create_new_conversation()
        
        # Delete the conversation
        del st.session_state.conversations[conversation_id]

def main():
    # Set page config
    st.set_page_config(
        page_title="ASA Medical Assistant",
        page_icon="🏥",
        layout="centered",
        initial_sidebar_state="expanded"
    )
    
    # Add custom CSS for styling
    st.markdown("""
    <style>
    /* ASA BOLNICA branding */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons');
    
    /* Sidebar styling */
    div[data-testid="stSidebarContent"] {
        background-color: #003B7A;
        color: white;
    }
    
    /* Button styling */
    .stButton button {
        width: 100%;
        border-radius: 6px !important;
        height: 44px;
        background-color: #0055AA !important;
        color: white !important;
        border: 1px solid #0066CC !important;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Roboto', sans-serif;
        font-weight: 500;
    }
    .stButton button:hover {
        background-color: #0066CC !important;
    }
    
    /* Option menu styling */
    .st-emotion-cache-16txtl3 h1 {
        font-size: 14px !important;
        color: #E0E0E0 !important;
        font-weight: 500 !important;
        padding-left: 10px !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-family: 'Roboto', sans-serif;
    }
    
    /* Conversation ID styling */
    .conv-id {
        font-weight: bold;
        color: #FFFFFF;
    }
    
    .conv-time {
        font-size: 0.8em;
        color: #CCDDEE;
    }
    
    /* Header styling */
    h1 {
        color: #003B7A !important;
        font-family: 'Roboto', sans-serif;
        font-weight: 700;
    }
    
    /* Chat container */
    div[data-testid="stChatMessageContent"] {
        background-color: #E6EEF8;
        border-radius: 8px;
        padding: 10px;
    }
    
    /* Assistant chat bubbles */
    .stChatMessage[data-testid="stChatMessageContent"] {
        background-color: #E6EEF8;
    }
    
    /* User chat bubbles */
    .stChatMessage[data-testid="user"] > div {
        background-color: #003B7A;
        color: white;
    }
    
    /* Chat input box */
    div[data-testid="stChatInput"] > div {
        border-color: #003B7A;
    }
    
    /* ASA BOLNICA logo styling for header */
    .logo-header {
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
    }
    .logo-header img {
        height: 60px;
    }
    
    /* Material icons in buttons */
    .material-icons {
        font-size: 16px;
        margin-right: 8px;
        vertical-align: middle;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar for conversation history
    with st.sidebar:
        # Logo in sidebar
        st.markdown("""
        <div style="text-align:center; margin-bottom:20px; margin-top:10px;">
            <h2 style="color:white; font-family:'Roboto',sans-serif; font-weight:700; margin-bottom:5px;">ASA BOLNICA</h2>
            <p style="color:#CCDDEE; font-size:14px; margin-top:0;">Medical Assistant</p>
        </div>
        """, unsafe_allow_html=True)
        
        # New conversation button at top
        if st.button('New chat', type="secondary", key="new_chat_btn"):
            create_new_conversation()
            st.rerun()
        
        st.divider()
        
        # Simple sorting by ID (most recent first)
        sorted_conversations = sorted(
            st.session_state.conversations.items(),
            key=lambda x: x[1]["created_at"],
            reverse=True
        )
        
        # Prepare lists for option menu
        conv_list = []
        conv_ids = []
        
        for conv_id, conv_data in sorted_conversations:
            # Get a short conversation ID (first 6 characters)
            short_id = conv_id[:6]
            
            # Format creation time
            creation_time = conv_data["created_at"]
            
            # Create simple text-based title
            title = f"#{short_id} • {creation_time}"
            
            conv_list.append(title)
            conv_ids.append(conv_id)
        
        # Display conversations
        if conv_list:
            selected_index = 0
            if st.session_state.current_conversation_id in conv_ids:
                selected_index = conv_ids.index(st.session_state.current_conversation_id)
            
            # Show conversation menu
            selected_conversation = option_menu(
                menu_title="Conversations",
                options=conv_list,
                icons=["chat-left-text"] * len(conv_list),  # Using Bootstrap icons
                default_index=selected_index,
                orientation="vertical",
                styles={
                    "container": {"padding": "0!important", "background-color": "#003B7A"},
                    "icon": {"color": "#FFFFFF", "font-size": "16px"},
                    "nav-link": {
                        "font-size": "14px", 
                        "text-align": "left", 
                        "margin": "3px 0", 
                        "--hover-color": "#0055AA", 
                        "white-space": "normal",
                        "height": "auto",
                        "padding": "10px 15px",
                        "color": "#FFFFFF",
                        "border-radius": "6px",
                        "font-family": "'Roboto', sans-serif"
                    },
                    "nav-link-selected": {"background-color": "#0055AA", "color": "#FFFFFF"},
                    "menu-title": {"color": "#CCDDEE", "font-size": "12px", "font-weight": "500", "margin-top": "12px", "margin-bottom": "5px", "font-family": "'Roboto', sans-serif"}
                }
            )
            
            # Set the current conversation based on selection
            selected_index = conv_list.index(selected_conversation)
            selected_conv_id = conv_ids[selected_index]
            if selected_conv_id != st.session_state.current_conversation_id:
                set_current_conversation(selected_conv_id)
                st.rerun()
        
        # Bottom section for delete button
        st.markdown("<div style='position: fixed; bottom: 20px; width: 85%;'>", unsafe_allow_html=True)
        
        # Delete conversation button
        if st.session_state.conversations and len(st.session_state.conversations) > 1:
            if st.button('Delete chat', type="secondary"):
                delete_conversation(st.session_state.current_conversation_id)
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Main chat area with header
    st.markdown("""
    <div class="logo-header">
        <h1>ASA Medical Assistant</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Get current conversation data
    current_chat_history = st.session_state.conversations[st.session_state.current_conversation_id]["chat_history"]
    
    # Create a container for chat messages
    chat_container = st.container()
    
    # Display the chat history
    with chat_container:
        if current_chat_history:
            for msg_pair in current_chat_history:
                # User message
                if "user" in msg_pair and msg_pair["user"]:
                    with st.chat_message("user", avatar=":material/face:"):
                        st.markdown(msg_pair["user"])
                
                # Assistant message
                if "assistant" in msg_pair and msg_pair["assistant"]:
                    with st.chat_message("assistant", avatar=":material/health_and_safety:"):
                        # Use markdown rendering explicitly to handle the structured format
                        st.markdown(msg_pair["assistant"])
        else:
            # Intro if chat_history is empty
            with st.chat_message("assistant", avatar=":material/health_and_safety:"):
                st.markdown("Welcome to ASA Medical Assistant! How can I help you today?")
    
    # Chat input at the bottom
    prompt = st.chat_input("Enter your medical query...")
    if prompt:
        # Add user message to chat history and rerun to show it immediately
        current_chat_history.append({"user": prompt})
        st.rerun()

    # Check if we need to generate a response
    if current_chat_history and "user" in current_chat_history[-1]:
        last_message = current_chat_history[-1]
        if "assistant" not in last_message:  # Only respond if we haven't already
            # Create a placeholder for the streaming response
            with st.chat_message("assistant", avatar=":material/health_and_safety:"):
                message_placeholder = st.empty()
                
                # Process streaming response
                response_stream = get_medical_assistant_response(
                    last_message["user"],
                    current_chat_history
                )
                
                # Process the streaming response with format enforcement
                formatted_response = process_stream_with_format_enforcement(
                    response_stream, 
                    message_placeholder
                )
                
                # Add the formatted response to chat history
                current_chat_history[-1]["assistant"] = formatted_response
                
                # No longer update conversation title based on first message

if __name__ == "__main__":
    main()
