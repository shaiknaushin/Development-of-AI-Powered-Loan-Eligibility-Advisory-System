from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from .models import CreditApplication
import os
import json

def create_report_pdf(app: CreditApplication) -> str:
    """Generates a PDF report for a credit application, using the new data model."""
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    file_path = os.path.join(reports_dir, f"report_app_{app.id}.pdf")

    doc = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Credit Underwriting Report", styles['h1']))
    story.append(Spacer(1, 24))

    story.append(Paragraph("Applicant Details", styles['h2']))
    # Updated to include new fields from the detailed chatbot
    data = [
        ["Application ID:", str(app.id)],
        ["Full Name:", app.full_name or "N/A"],
        ["Gender:", app.gender or "N/A"],
        ["Married:", app.married or "N/A"],
        ["Dependents:", app.dependents or "N/A"],
        ["Education:", app.education or "N/A"],
        ["Self Employed:", app.self_employed or "N/A"],
        ["Property Area:", app.property_area or "N/A"],
        ["Monthly Income:", f"₹ {app.monthly_income:,.2f}" if app.monthly_income is not None else "N/A"],
        ["Co-applicant Income:", f"₹ {app.coapplicant_income:,.2f}" if app.coapplicant_income is not None else "N/A"],
        ["Loan Amount:", f"₹ {app.loan_amount:,.2f}" if app.loan_amount is not None else "N/A"],
        ["Loan Term (Months):", str(app.loan_amount_term) if app.loan_amount_term is not None else "N/A"],
        ["Credit History Meets Guidelines:", "Yes" if app.credit_history == 1 else "No"],
    ]
    story.append(create_styled_table(data))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Final Decision & Details", styles['h2']))
    
    decision = app.final_decision or "Pending"
    result_color = colors.green if decision == "Approved" else colors.red
    result_text = f"<font color='{result_color}'><b>{decision}</b></font>"
    score_text = f"{app.final_score * 100:.2f}%" if app.final_score is not None else "N/A"
    
    reasons_text = "N/A"
    if app.decision_reasons:
        try:
            reasons_dict = json.loads(app.decision_reasons)
            reasons_text = ", ".join([f"{k}: {v}" for k, v in reasons_dict.items()])
        except (json.JSONDecodeError, TypeError):
            reasons_text = str(app.decision_reasons)

    prediction_data = [
        ["Final Decision:", Paragraph(result_text, styles['Normal'])],
        ["Confidence Score:", score_text],
        ["Key Factors (Reasons):", reasons_text]
    ]
    story.append(create_styled_table(prediction_data))
    story.append(Spacer(1, 24))

    timestamp = app.created_at.strftime('%Y-%m-%d %H:%M') if app.created_at else "N/A"
    story.append(Paragraph(f"Report Generated On: {timestamp}", styles['Normal']))

    doc.build(story)
    return file_path

def create_styled_table(data):
    """Helper to create a styled table for the PDF."""
    table = Table(data, hAlign='LEFT', colWidths=['40%', '60%'])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.darkslategray),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    return table

