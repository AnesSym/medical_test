import streamlit as st
from groq import Groq
import os
import pandas as pd
from datetime import datetime
from io import BytesIO
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# Import prompts
from prompts import (
    BASIC_ASSISTANT_PROMPT,
    MEDICAL_TRIAGE_PROMPT,
    DIAGNOSTIC_ANALYSIS_PROMPT,
    SPECIAL_RESPONSE_PROMPT,
    SPECIAL_PROMPTS,
    DIAGNOSTIC_ANALYSIS_TEMPLATE,
    PATIENT_CONTEXT_TEMPLATE
)

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

# Initialize list of API keys
API_KEYS = [
    "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",
    "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",
    "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"
]

def get_next_api_key():
    """Rotate through API keys"""
    current_key = API_KEYS[st.session_state.api_key_index]
    st.session_state.api_key_index = (st.session_state.api_key_index + 1) % len(API_KEYS)
    return current_key

def get_groq_client():
    """Get Groq client with next API key"""
    return Groq(api_key=get_next_api_key())

def get_assistant_response(prompt, chat_history):
    client = get_groq_client()  # Get client with next API key
    # Prepare messages including chat history
    messages = [
        {"role": "system", "content": BASIC_ASSISTANT_PROMPT}
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
    
    # Format the prompt using the template
    prompt = DIAGNOSTIC_ANALYSIS_TEMPLATE.format(
        age=patient_data['age'],
        gender=patient_data['gender'],
        symptoms=patient_data['symptoms'],
        medical_conditions=', '.join(patient_data['medical_conditions']),
        medications=patient_data['medications'],
        allergies=patient_data['allergies'],
        temperature=patient_data['temperature'],
        heart_rate=patient_data['heart_rate'],
        blood_pressure=patient_data['blood_pressure'],
        oxygen_saturation=patient_data['oxygen_saturation']
    )
    
    messages = [
        {
            "role": "system",
            "content": DIAGNOSTIC_ANALYSIS_PROMPT
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

def enforce_structured_output(text):
    """
    This function is no longer needed as we're using native markdown formatting.
    Keeping as a placeholder in case we need to validate markdown structure in the future.
    """
    return text

def process_stream_with_format_enforcement(response_stream, message_placeholder):
    """
    Process streaming response without format enforcement since we're now
    relying on markdown formatting.
    """
    full_response = ""
    for chunk in response_stream:
        if chunk.choices[0].delta.content is not None:
            full_response += chunk.choices[0].delta.content
            # Display the markdown as is without enforcement
            message_placeholder.markdown(full_response + "▌")
    
    # Final update with the complete response
    message_placeholder.markdown(full_response)
    
    return full_response

def get_medical_assistant_response(prompt, chat_history, patient_data=None):
    client = get_groq_client()  # Get client with next API key
    
    messages = [{"role": "system", "content": MEDICAL_TRIAGE_PROMPT}]
    
    # Add patient context if available
    if patient_data:
        patient_context = PATIENT_CONTEXT_TEMPLATE.format(
            name=patient_data['name'],
            age=patient_data['age'],
            gender=patient_data['gender'],
            blood_pressure=patient_data['blood_pressure'],
            heart_rate=patient_data['heart_rate'],
            temperature=patient_data['temperature'],
            symptoms=patient_data['symptoms']
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
    
    # Parameters optimized for markdown generation
    return client.chat.completions.create(
        messages=messages,
        model="Llama-3.3-70B-Versatile",
        temperature=0.4,     # Lower temperature for more consistent outputs
        max_tokens=1024,
        top_p=0.95,          # Higher top_p for more deterministic output
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stream=True          # Enable streaming
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
    
    # Format the system prompt with the prompt type
    formatted_system_prompt = SPECIAL_RESPONSE_PROMPT.format(prompt_type=prompt_type)
    
    messages = [
        {"role": "system", "content": formatted_system_prompt},
        # Add the conversation history
        *[msg for msg in chat_history if msg.get("assistant") and "Summary" not in msg.get("assistant")],
        # Add the special prompt
        {"role": "user", "content": SPECIAL_PROMPTS[prompt_type]}
    ]
    
    return client.chat.completions.create(
        messages=messages,
        model="llama3-70b-8192",
        temperature=0.5,
        max_tokens=1024,
        top_p=1,
        stream=True
    )

def send_feedback_email(chat_history, feedback_text):
    """Send feedback via email"""
    # Email configuration
    sender_email = os.getenv('FEEDBACK_EMAIL')
    sender_password = os.getenv('FEEDBACK_EMAIL_PASSWORD')
    receiver_email = os.getenv('FEEDBACK_EMAIL')  # Same as sender in this case
    
    if not all([sender_email, sender_password, receiver_email]):
        st.error("Email configuration is missing. Please check environment variables.")
        return False
        
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = f"Medical Assistant Feedback - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Format the chat history
        chat_summary = "\n".join([
            f"User: {msg.get('user', '')}\nAssistant: {msg.get('assistant', '')}"
            for msg in chat_history
        ])
        
        # Create email body
        body = f"""
New Feedback Received:

Feedback:
{feedback_text}

Chat History:
{chat_summary}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Create SMTP session
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        return True
    except Exception as e:
        st.error(f"Error sending feedback: {str(e)}")
        return False 