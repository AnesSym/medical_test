import streamlit as st
from groq import Groq
import os
import pandas as pd
from datetime import datetime
from io import BytesIO


# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import LETTER, inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph, 
    SimpleDocTemplate, 
    Spacer, 
    Table, 
    TableStyle
)

# Load environment variables

# Initialize list of API keys
API_KEYS = [
    "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",
    "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",
    "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"
]

# Add key rotation counter to session state
if "api_key_index" not in st.session_state:
    st.session_state.api_key_index = 0

def get_next_api_key():
    """Rotate through API keys"""
    current_key = API_KEYS[st.session_state.api_key_index]
    st.session_state.api_key_index = (st.session_state.api_key_index + 1) % len(API_KEYS)
    return current_key

# Replace the static client initialization with a function
def get_groq_client():
    """Get Groq client with next API key"""
    return Groq(api_key=get_next_api_key())

def get_assistant_response(prompt, chat_history):
    client = get_groq_client()  # Get client with next API key
    # Prepare messages including chat history
    messages = [
        {"role": "system", "content": "You are a helpful and knowledgeable Medical assistant."}
    ]
    
    # Add chat history to messages
    for message in chat_history:
        if "user" in message:
            messages.append({"role": "user", "content": message["user"]})
        if "assistant" in message:
            messages.append({"role": "assistant", "content": message["assistant"]})
    
    # Add current user prompt
    messages.append({"role": "user", "content": prompt})
    
    # Get response from Groq
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="llama3-70b-8192",  # adjust if needed
        temperature=0.5,
        max_tokens=500,
        top_p=1,
        stream=False
    )
    
    return chat_completion.choices[0].message.content

def create_patient_intake_form():
    st.header("Patient Intake Form")
    
    # Demographics Section
    st.subheader("Demographics")
    col1, col2 = st.columns(2)
    
    with col1:
        patient_name = st.text_input("Patient Name")
        age = st.number_input("Age", min_value=0, max_value=120)
        gender = st.selectbox("Gender", ["Select", "Male", "Female", "Other"])
    
    with col2:
        height = st.number_input("Height (cm)", min_value=0.0)
        weight = st.number_input("Weight (kg)", min_value=0.0)
        date = st.date_input("Date of Visit", datetime.now())

    # Medical History Section
    st.subheader("Medical History")
    medical_conditions = st.multiselect(
        "Known Medical Conditions",
        ["Diabetes", "Hypertension", "Heart Disease", "Asthma", "Cancer", "None"],
        default=["None"]
    )
    
    medications = st.text_area("Current Medications (one per line)")
    allergies = st.text_area("Known Allergies (one per line)")

    # Symptoms Section
    st.subheader("Current Symptoms")
    symptoms = st.text_area("Please describe current symptoms")
    
    # File Upload
    st.subheader("Medical Records")
    uploaded_files = st.file_uploader(
        "Upload relevant medical records (lab results, imaging, etc.)", 
        accept_multiple_files=True
    )

    # Vitals Section
    st.subheader("Vitals")
    col3, col4 = st.columns(2)
    
    with col3:
        temperature = st.number_input("Temperature (°C)", min_value=35.0, max_value=43.0, value=37.0)
        heart_rate = st.number_input("Heart Rate (bpm)", min_value=0, max_value=220)
    
    with col4:
        bp_systolic = st.number_input("Blood Pressure - Systolic", min_value=0, max_value=250)
        bp_diastolic = st.number_input("Blood Pressure - Diastolic", min_value=0, max_value=200)
        oxygen_saturation = st.number_input("Oxygen Saturation (%)", min_value=0, max_value=100, value=98)

    # Submit Button
    if st.button("Submit Patient Data"):
        # Create a dictionary of all patient data
        patient_data = {
            "name": patient_name,
            "age": age,
            "gender": gender,
            "height": height,
            "weight": weight,
            "date": date,
            "medical_conditions": medical_conditions,
            "medications": medications,
            "allergies": allergies,
            "symptoms": symptoms,
            "temperature": temperature,
            "heart_rate": heart_rate,
            "blood_pressure": f"{bp_systolic}/{bp_diastolic}",
            "oxygen_saturation": oxygen_saturation
        }
        
        # Store in session state
        if "patient_records" not in st.session_state:
            st.session_state.patient_records = []
        
        st.session_state.patient_records.append(patient_data)
        st.success("Patient data submitted successfully!")
        
        return patient_data
    
    return None

def get_diagnostic_analysis(patient_data):
    client = get_groq_client()  # Get client with next API key
    # Prepare a comprehensive prompt for the LLM
    prompt = f"""As a medical AI assistant, please analyze the following patient information and provide 
potential diagnoses and recommendations.
The analysis should be in the form of a medical report. and should be short and concise.
If the input data appears to be erroneous or incomplete, respond professionally indicating the issue.
if there is some data that looks like it is not correct based on other data, respond professionally indicating the issue.
Patient Details:
- Age: {patient_data['age']}
- Gender: {patient_data['gender']}
- Current Symptoms: {patient_data['symptoms']}
- Medical History: {', '.join(patient_data['medical_conditions'])}
- Current Medications: {patient_data['medications']}
- Allergies: {patient_data['allergies']}
- Vitals:
  * Temperature: {patient_data['temperature']}°C
  * Heart Rate: {patient_data['heart_rate']} bpm
  * Blood Pressure: {patient_data['blood_pressure']}
  * Oxygen Saturation: {patient_data['oxygen_saturation']}%

Please provide:
1. which department or specialist the user should contact (e.g., Cardiology, Neurology, Infectious Diseases, etc.).

Note: This is AI-generated and does not replace professional medical judgment.
"""
    messages = [
        {
            "role": "system",
            "content": "You are a knowledgeable medical AI assistant providing professional analysis."
        },
        {"role": "user", "content": prompt}
    ]
    
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="llama3-70b-8192",
        temperature=0.3,
        max_tokens=500,
        top_p=1,
        stream=False
    )
    
    return chat_completion.choices[0].message.content

def create_medical_report(patient_data, analysis):
    """
    A simple text-based report (if you still want text output).
    """
    current_date = datetime.now().strftime("%d/%m/%Y")
    
    report = f"""
MEDICAL REPORT
Date of Report: {current_date}
=======================================================

PATIENT INFORMATION (Status Praesens)
-----------------------------------
Name: {patient_data['name']}
Date of Visit: {patient_data['date']}
Gender: {patient_data['gender']}
Age: {patient_data['age']} years
Height: {patient_data['height']} cm
Weight: {patient_data['weight']} kg

VITAL SIGNS (Signa Vitalia)
--------------------------
Temperature: {patient_data['temperature']}°C
Blood Pressure: {patient_data['blood_pressure']} mmHg
Heart Rate: {patient_data['heart_rate']} bpm
O₂ Saturation: {patient_data['oxygen_saturation']}%

MEDICAL HISTORY (Anamnesis)
-------------------------
Known Conditions (Status Morbi): 
{', '.join(patient_data['medical_conditions'])}

Current Medications (Medicatio Actualis):
{patient_data['medications'] or 'None reported'}

Allergies (Allergiae):
{patient_data['allergies'] or 'None reported'}

CURRENT SYMPTOMS (Symptomata)
---------------------------
{patient_data['symptoms']}

ANALYSIS AND ASSESSMENT
---------------------
{analysis}

-------------------
NOTICE: This report includes AI-assisted analysis and should be reviewed by a licensed medical professional.
Generated via Medical Assistant System
"""
    return report

def get_medical_assistant_response(prompt, chat_history, patient_data=None):
    client = get_groq_client()  # Get client with next API key
    # Updated system prompt to follow the specified workflow
    system_prompt = (
        "You are an advanced medical AI triage assistant for ASA bolnica in Bosnia and Herzegovina. "
        "Your role is to help patients with their initial medical inquiries and direct them "
        "to the appropriate departments within ASA bolnica. "
        "Keep your responses short, clear, and well-structured.\n\n"
        "When gathering information, format your response like this:\n\n"
        "**Reported Symptoms:**\n"
        "• [Symptom] - [Duration] - [Severity]\n"
        "• [Symptom] - [Duration] - [Severity]\n\n"
        "**Additional Information Needed:**\n"
        "[List your follow-up questions here]\n\n"
        "Only when you have gathered ALL necessary information about the symptoms, "
        "provide your final response in this format:\n\n"
        "**Reported Symptoms:**\n"
        "• [Symptom] - [Duration] - [Severity]\n"
        "• [Symptom] - [Duration] - [Severity]\n\n"
        "**Recommendation:**\n"
        "[Your referral recommendation to specific ASA bolnica department]\n\n"
        "---\n"
        "**Summary**\n\n"
        "**Key Symptoms:**\n"
        "[List main symptoms]\n\n"
        "**Recommended Department/Specialist:**\n"
        "[Department at ASA bolnica]\n\n"
        "**Urgency Level:**\n"
        "[Choose one of the following:]\n"
        "- Immediate (Emergency Room visit needed now)\n"
        "- Very Soon (Within 24 hours)\n"
        "- Priority (Within 2-3 days)\n"
        "- Standard (Within 1-2 weeks)\n"
        "- Routine (Next available appointment)\n"
        "---\n\n"
        "Important guidelines:\n"
        "1. Do NOT show the summary section until you have gathered all necessary information\n"
        "2. While gathering information, only show Reported Symptoms and Additional Information Needed\n"
        "3. Keep responses concise and professional\n"
        "4. Do not provide diagnosis - only referral recommendations to ASA bolnica departments\n"
        "5. Use bullet points (•) for listing symptoms\n"
        "6. Always ask follow-up questions if information is incomplete\n"
        "7. Remember you are representing ASA bolnica in Bosnia and Herzegovina"
    )
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add patient context if available
    if patient_data:
        patient_context = (
            f"Current patient context:\n"
            f"- Name: {patient_data['name']}\n"
            f"- Age: {patient_data['age']}\n"
            f"- Gender: {patient_data['gender']}\n"
            f"- Vitals: BP {patient_data['blood_pressure']}, "
            f"HR {patient_data['heart_rate']}, Temp {patient_data['temperature']}°C\n"
            f"- Current Symptoms: {patient_data['symptoms']}"
        )
        messages.append({"role": "system", "content": patient_context})
    
    # Add chat history to the conversation
    for message in chat_history:
        if "user" in message:
            messages.append({"role": "user", "content": message["user"]})
        if "assistant" in message:
            messages.append({"role": "assistant", "content": message["assistant"]})
    
    # Add current prompt
    messages.append({"role": "user", "content": prompt})
    
    return client.chat.completions.create(
        messages=messages,
        model="llama3-70b-8192",
        temperature=0.9,
        max_tokens=1024,
        top_p=1,
        stream=True  # Enable streaming
    )

def check_medical_alerts(text):
    """Check for emergency medical conditions in the text"""
    emergency_keywords = [
        "stroke", "heart attack", "myocardial infarction", "sepsis", 
        "anaphylaxis", "pulmonary embolism", "meningitis", "acute",
        "immediate", "emergency", "urgent", "critical"
    ]
    
    has_emergency = any(keyword in text.lower() for keyword in emergency_keywords)
    return has_emergency

# ========== NEW PDF GENERATION FUNCTION ==========
import re
import re

def convert_md_to_html(md_text: str) -> str:
    """
    Naive conversion of Markdown-like text:
      - Replace **bold** markers with <b>...</b>
      - Replace line breaks with <br/>
    """
    # Convert **bold** to <b>...</b>
    html_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', md_text)
    # Replace line breaks with <br/>
    html_text = html_text.replace('\n', '<br/>')
    return html_text

def strip_before_marker(text: str, marker: str = "**Analysis**") -> str:
    """
    Return only the substring starting at the given 'marker'.
    Case-insensitive. If marker not found, returns the original text.
    """
    text_lower = text.lower()
    marker_lower = marker.lower()
    
    idx = text_lower.find(marker_lower)
    if idx != -1:
        # Keep everything from the marker onward
        return text[idx:]
    else:
        return text


def generate_pdf_report(patient_data, analysis):
    """
    Generate a styled PDF medical report using ReportLab and return it as a BytesIO object.
    This version only includes everything under the '**Analysis**' marker.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    elements = []
    
    # Grab some built-in styles (feel free to customize)
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    normal_style = styles["BodyText"]
    
    # ---- Title ----
    elements.append(Paragraph("MEDICAL REPORT", title_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # ---- Date of Report ----
    report_date = datetime.now().strftime("%d/%m/%Y")
    elements.append(Paragraph(f"<b>Date of Report:</b> {report_date}", normal_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # ---- Patient Information ----
    elements.append(Paragraph("PATIENT INFORMATION (Status Praesens)", heading_style))
    patient_info_table_data = [
        ["Name:", patient_data['name']],
        ["Date of Visit:", str(patient_data['date'])],
        ["Gender:", patient_data['gender']],
        ["Age:", str(patient_data['age'])],
        ["Height:", f"{patient_data['height']} cm"],
        ["Weight:", f"{patient_data['weight']} kg"],
    ]
    patient_info_table = Table(patient_info_table_data)
    patient_info_table.hAlign = 'LEFT'
    patient_info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0,0), (1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(patient_info_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # ---- Vital Signs ----
    elements.append(Paragraph("VITAL SIGNS (Signa Vitalia)", heading_style))
    vitals_table_data = [
        ["Temperature:", f"{patient_data['temperature']} °C"],
        ["Blood Pressure:", patient_data['blood_pressure']],
        ["Heart Rate:", f"{patient_data['heart_rate']} bpm"],
        ["O2 Saturation:", f"{patient_data['oxygen_saturation']} %"],
    ]
    vitals_table = Table(vitals_table_data)
    vitals_table.hAlign = 'LEFT'
    vitals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BACKGROUND', (0,0), (1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(vitals_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # ---- Medical History ----
    elements.append(Paragraph("MEDICAL HISTORY (Anamnesis)", heading_style))
    known_conditions = ', '.join(patient_data['medical_conditions'])
    med_history_text = f"""
    <b>Known Conditions (Status Morbi):</b> {known_conditions}<br/>
    <b>Current Medications (Medicatio Actualis):</b> {patient_data['medications'] or 'None reported'}<br/>
    <b>Allergies (Allergiae):</b> {patient_data['allergies'] or 'None reported'}
    """
    elements.append(Paragraph(med_history_text, normal_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # ---- Current Symptoms ----
    elements.append(Paragraph("CURRENT SYMPTOMS (Symptomata)", heading_style))
    elements.append(Paragraph(patient_data['symptoms'], normal_style))
    elements.append(Spacer(1, 0.3 * inch))
    
    # ---- Analysis and Assessment ----
    # 1) Strip out everything before "**Analysis**" in your raw text from the LLM
    cleaned_analysis = strip_before_marker(analysis, "**Potential Diagnoses:**")
    # 2) Convert from MD-like text to HTML
    parsed_analysis = convert_md_to_html(cleaned_analysis)
    
    elements.append(Paragraph("ANALYSIS AND ASSESSMENT", heading_style))
    elements.append(Paragraph(parsed_analysis, normal_style))
    elements.append(Spacer(1, 0.3 * inch))
    
    # ---- Disclaimer ----
    disclaimer = (
        "NOTICE: This report includes AI-assisted analysis and should be "
        "reviewed by a licensed medical professional."
    )
    elements.append(Paragraph(disclaimer, styles["Italic"]))
    
    # Build the PDF
    doc.build(elements)
    
    # Retrieve the PDF from buffer
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

def get_special_response(prompt_type, chat_history):
    client = get_groq_client()  # Get client with next API key
    """Handle special response types like clinical reasoning and medical literature"""
    
    special_prompts = {
        "clinical_reasoning": (
            "Based on our conversation so far, here is my clinical reasoning process:\n\n"
            "1. Review the reported symptoms and their characteristics\n"
            "2. Consider the timeline and progression\n"
            "3. Evaluate risk factors and severity\n"
            "4. Determine appropriate specialist referral\n\n"
            "Please explain your clinical reasoning process for the previous recommendation."
        ),
        "medical_literature": (
            "Based on the symptoms and conditions discussed, please provide relevant medical "
            "literature references and guidelines that support your recommendation. Include "
            "standard medical guidelines and protocols where applicable."
        )
    }
    
    # Get the appropriate prompt
    system_prompt = (
        "You are a medical AI assistant. Provide a detailed but concise response "
        "focusing specifically on {prompt_type}. Reference established medical "
        "guidelines and literature where appropriate. Keep the response professional "
        "and evidence-based."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        # Add the conversation history
        *[msg for msg in chat_history if msg.get("assistant") and "Summary" not in msg.get("assistant")],
        # Add the special prompt
        {"role": "user", "content": special_prompts[prompt_type]}
    ]
    
    return client.chat.completions.create(
        messages=messages,
        model="llama3-70b-8192",
        temperature=0.5,
        max_tokens=1024,
        top_p=1,
        stream=True
    )

def main():
    # Set page config with no sidebar
    st.set_page_config(
        page_title="ASA Medical Assistant",
        page_icon="🏥",
        layout="centered",
        initial_sidebar_state="collapsed"  # This hides the sidebar by default
    )
    
    # Initialize session states
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "patient_records" not in st.session_state:
        st.session_state.patient_records = []
    if "patient_analyses" not in st.session_state:
        st.session_state.patient_analyses = {}

    # Main chat area
    st.header("ASA Medical Assistant")
    
    # Create a container for chat messages
    chat_container = st.container()
    
    with chat_container:
        # Display the chat history
        if st.session_state.chat_history:
            for msg_pair in st.session_state.chat_history:
                # User message
                if "user" in msg_pair and msg_pair["user"]:
                    with st.chat_message("user"):
                        st.write(msg_pair["user"])
                # Assistant message
                if "assistant" in msg_pair and msg_pair["assistant"]:
                    with st.chat_message("assistant"):
                        st.markdown(msg_pair["assistant"])
        else:
            # Intro if chat_history is empty
            st.info("Welcome to ASA Medical Assistant! How can I help you today?")
    
    # Chat input at the bottom
    prompt = st.chat_input("Enter your medical query...")
    if prompt:
        # Add user message to chat history and rerun to show it immediately
        st.session_state.chat_history.append({"user": prompt})
        st.rerun()

    # Check if we need to generate a response
    if st.session_state.chat_history and "user" in st.session_state.chat_history[-1]:
        last_message = st.session_state.chat_history[-1]
        if "assistant" not in last_message:  # Only respond if we haven't already
            # Create a placeholder for the streaming response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                # Stream the response
                for chunk in get_medical_assistant_response(
                    last_message["user"],
                    st.session_state.chat_history
                ):
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                
                # Update the placeholder with the complete response
                message_placeholder.markdown(full_response)
            
            # Add the complete response to chat history
            st.session_state.chat_history[-1]["assistant"] = full_response

if __name__ == "__main__":
    main()
