from io import BytesIO
from reportlab.lib.pagesizes import LETTER, inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from datetime import datetime
def generate_pdf_report(patient_data, analysis):
    """
    Generate a styled PDF medical report using ReportLab and return it as a BytesIO object.
    """
    # Create a BytesIO buffer to receive PDF data
    buffer = BytesIO()
    
    # Create a SimpleDocTemplate object using letter page size
    doc = SimpleDocTemplate(buffer, pagesize=LETTER,
                            rightMargin=72,
                            leftMargin=72,
                            topMargin=72,
                            bottomMargin=72)
    
    # Use a list to build up PDF elements
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    normal_style = styles["BodyText"]
    
    # Title
    elements.append(Paragraph("MEDICAL REPORT", title_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Date
    report_date = datetime.now().strftime("%d/%m/%Y")
    elements.append(Paragraph(f"<b>Date of Report:</b> {report_date}", normal_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Patient Info
    elements.append(Paragraph("PATIENT INFORMATION (Status Praesens)", heading_style))
    patient_info_table = Table([
        ["Name:", patient_data['name']],
        ["Date of Visit:", str(patient_data['date'])],
        ["Gender:", patient_data['gender']],
        ["Age:", str(patient_data['age'])],
        ["Height:", f"{patient_data['height']} cm"],
        ["Weight:", f"{patient_data['weight']} kg"],
    ])
    patient_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(patient_info_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Vital Signs
    elements.append(Paragraph("VITAL SIGNS (Signa Vitalia)", heading_style))
    vitals_table = Table([
        ["Temperature:", f"{patient_data['temperature']} °C"],
        ["Blood Pressure:", patient_data['blood_pressure']],
        ["Heart Rate:", f"{patient_data['heart_rate']} bpm"],
        ["O₂ Saturation:", f"{patient_data['oxygen_saturation']} %"]
    ])
    vitals_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(vitals_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Medical History
    elements.append(Paragraph("MEDICAL HISTORY (Anamnesis)", heading_style))
    known_conditions = ', '.join(patient_data['medical_conditions'])
    med_history_text = f"""
    <b>Known Conditions (Status Morbi):</b> {known_conditions}<br/>
    <b>Current Medications (Medicatio Actualis):</b> {patient_data['medications'] or 'None reported'}<br/>
    <b>Allergies (Allergiae):</b> {patient_data['allergies'] or 'None reported'}
    """
    elements.append(Paragraph(med_history_text, normal_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Current Symptoms
    elements.append(Paragraph("CURRENT SYMPTOMS (Symptomata)", heading_style))
    symptoms_text = f"{patient_data['symptoms']}"
    elements.append(Paragraph(symptoms_text, normal_style))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Analysis and Assessment
    elements.append(Paragraph("ANALYSIS AND ASSESSMENT", heading_style))
    elements.append(Paragraph(analysis, normal_style))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Disclaimer
    disclaimer = "NOTICE: This report includes AI-assisted analysis and should be reviewed by a licensed medical professional."
    elements.append(Paragraph(disclaimer, styles["Italic"]))
    
    # Build the PDF
    doc.build(elements)
    
    # Retrieve the PDF from the buffer
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data