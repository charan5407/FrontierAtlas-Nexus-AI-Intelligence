"""
Formal Cover Letter & Video Walkthrough Extension Request Generator.
Typeset in Times-Roman for P Charan, AI Engineer Internship Assessment.
Formatted to fit cleanly on exactly ONE page.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)


def build_letter_pdf(output_path: str = "Submission_Cover_Letter_P_Charan.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=50,
        rightMargin=50,
        topMargin=40,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    PRIMARY = colors.HexColor("#0F172A")
    TEXT = colors.HexColor("#1E293B")
    MUTED = colors.HexColor("#475569")

    header_name = ParagraphStyle(
        'HeaderName',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=16,
        leading=20,
        textColor=PRIMARY
    )

    header_contact = ParagraphStyle(
        'HeaderContact',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=9,
        leading=13,
        textColor=MUTED
    )

    date_style = ParagraphStyle(
        'LetterDate',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=9.5,
        leading=13,
        textColor=PRIMARY,
        spaceBefore=6,
        spaceAfter=6
    )

    recipient_style = ParagraphStyle(
        'RecipientBlock',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=9.5,
        leading=13.5,
        textColor=PRIMARY,
        spaceAfter=8
    )

    subject_style = ParagraphStyle(
        'LetterSubject',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=10,
        leading=14,
        textColor=PRIMARY,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        'LetterBody',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=9.5,
        leading=13.5,
        textColor=TEXT,
        spaceAfter=7
    )

    bullet_style = ParagraphStyle(
        'LetterBullet',
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )

    sign_style = ParagraphStyle(
        'LetterSign',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=9.5,
        leading=13.5,
        textColor=PRIMARY,
        spaceBefore=8
    )

    story = []

    # Applicant Header
    header_data = [
        [
            Paragraph("<b>P CHARAN</b>", header_name),
            Paragraph("<b>Email:</b> charanchowdary5407@gmail.com<br/><b>Phone:</b> +91 7204575407<br/><b>GitHub:</b> github.com/charan5407", header_contact)
        ]
    ]
    header_table = Table(header_data, colWidths=[240, 272])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=4, spaceAfter=8))

    # Date
    story.append(Paragraph("<b>Date:</b> November 23, 2026", date_style))

    # Recipient
    recipient_text = (
        "<b>To:</b> The Technical Hiring & Evaluation Committee<br/>"
        "<b>The AI Signal / GraphOne / FrontierAtlas</b><br/>"
        "Re: AI Engineer Internship Assessment Submission"
    )
    story.append(Paragraph(recipient_text, recipient_style))

    # Subject
    story.append(Paragraph("<b>Subject: Submission of AI Engineer Demo Task & Request for Video Walkthrough Extension</b>", subject_style))

    # Salutation & Body
    story.append(Paragraph("Dear Hiring Committee,", body_style))

    p1 = (
        "I am submitting my completed deliverables for the <b>AI Engineer Internship</b> assessment ahead of today’s "
        "deadline (November 23, 2026, 7:00 PM). I have engineered, tested, and thoroughly documented the "
        "<b>FrontierAtlas Nexus</b> autonomous data ingestion pipeline, satisfying all six evaluation phases."
    )
    story.append(Paragraph(p1, body_style))

    p2 = "All technical deliverables are completed and accessible for review:"
    story.append(Paragraph(p2, body_style))

    story.append(Paragraph("• <b>GitHub Repository:</b> <u>https://github.com/charan5407/FrontierAtlas-Nexus-AI-Intelligence</u> (complete source code, 13 passing tests, one-click batch runners, and enterprise dark-mode dashboard).", bullet_style))
    story.append(Paragraph("• <b>Data Output (6 Tabs):</b> <i>FrontierAtlas_Data_Output.xlsx</i> containing 1,010 Startups, 1,010 Products, 1,010 Papers (with live GitHub stars), 24-hr fresh Jobs, 24-hr fresh News, and 1,112 Entity Mapping logs.", bullet_style))
    story.append(Paragraph("• <b>Technical Architecture Document:</b> <i>architecture.pdf</i> (publication-grade, strictly 3 pages).", bullet_style))
    story.append(Paragraph("• <b>Formal Technical Report:</b> <i>FrontierAtlas_Nexus_Technical_Report.pdf</i> (comprehensive documentation typeset in Times New Roman with complete academic references).", bullet_style))

    p3 = (
        "<b>Request for Video Walkthrough Extension:</b><br/>"
        "Due to an urgent, unforeseen emergency journey today, I am currently traveling and unable to record the video "
        "walkthrough with the quiet audio and professional presentation standard this project deserves. "
        "To honor today’s 7:00 PM deadline, I have submitted all source code, datasets, and architecture reports on time. "
        "I kindly request your permission for a short extension until <b>Wednesday (Nov 25) or Thursday (Nov 26)</b> "
        "to record and submit the video walkthrough demonstrating the live pipeline and dashboard."
    )
    story.append(Paragraph(p3, body_style))

    p4 = (
        "I am enthusiastic about contributing to The AI Signal / GraphOne team and look forward to discussing my "
        "implementation in detail. Thank you for your consideration, understanding, and support."
    )
    story.append(Paragraph(p4, body_style))

    # Closing & Signature
    sign_text = (
        "Sincerely,<br/>"
        "<b>P Charan</b><br/>"
        "Applicant — AI Engineer Internship<br/>"
        "<b>Phone:</b> +91 7204575407 &bull; <b>Email:</b> charanchowdary5407@gmail.com"
    )
    story.append(Paragraph(sign_text, sign_style))

    doc.build(story)
    print(f"[OK] Generated Formal Letter PDF: {output_path}")


if __name__ == "__main__":
    build_letter_pdf()
