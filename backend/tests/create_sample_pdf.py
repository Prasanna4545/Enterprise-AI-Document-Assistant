import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_sample_pdf(output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor='#1e293b',
        spaceAfter=12
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        textColor='#334155',
        spaceAfter=10
    )

    story = []

    # Page 1: Annual Vacation & Paid Leave Policy
    story.append(Paragraph("Acme Corporate Policy Manual 2026", title_style))
    story.append(Paragraph("Section 1: Annual Paid Vacation & Leave Policy", styles['Heading2']))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Full-time employees at Acme Corporation receive 28 days of paid annual vacation leave per calendar year. "
        "Vacation requests exceeding 5 consecutive business days require formal manager approval at least 14 days in advance. "
        "Unused vacation days up to a maximum of 5 days may be rolled over into the first quarter of the subsequent year.",
        body_style
    ))
    story.append(PageBreak())

    # Page 2: Remote Work & Home Office Allowance
    story.append(Paragraph("Section 2: Remote Work & Expense Reimbursement Policy", styles['Heading2']))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Employees working remotely are entitled to a quarterly home office reimbursement allowance of $450 USD. "
        "Eligible expenses include high-speed internet subscription invoices, ergonomic office chairs, and external display monitors. "
        "All expense receipts must be submitted through the finance portal within 30 days of purchase.",
        body_style
    ))
    story.append(PageBreak())

    # Page 3: IT Security & Password Policy
    story.append(Paragraph("Section 3: Device Security & Password Standards", styles['Heading2']))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "All corporate laptops must enforce full disk encryption using BitLocker or FileVault. "
        "Passwords must be at least 16 characters in length, combining uppercase letters, numbers, and symbols, and must be rotated every 90 days. "
        "Multi-Factor Authentication (MFA) is strictly mandatory for accessing company Google Workspace and GitHub repositories.",
        body_style
    ))

    doc.build(story)
    print(f"Sample PDF successfully generated at: {output_path}")

if __name__ == "__main__":
    generate_sample_pdf("tests/fixtures/Acme_Corporate_Policies_2026.pdf")
