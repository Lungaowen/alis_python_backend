import io
import gc
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart

def generate_report_bytes(task_id: str, document_title: str, client_id: int, analysis_result: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []
    
    # Theme colors
    risk_colors = {
        "HIGH": (colors.HexColor('#E24B4A'), colors.HexColor('#FCEBEB')),
        "MEDIUM": (colors.HexColor('#EF9F27'), colors.HexColor('#FAEEDA')),
        "LOW": (colors.HexColor('#639922'), colors.HexColor('#EAF3DE'))
    }
    
    overall_risk = analysis_result.get('riskLevel', 'MEDIUM').upper()
    border_color, bg_color = risk_colors.get(overall_risk, risk_colors["MEDIUM"])

    # PAGE 1 - COVER PAGE
    d = Drawing(400, 100)
    d.add(Rect(150, 40, 100, 40, fillColor=colors.HexColor('#1E3A8A'), strokeColor=colors.HexColor('#1E3A8A')))
    d.add(String(180, 55, 'ALIS', fontSize=20, fillColor=colors.white))
    elements.append(d)
    
    elements.append(Spacer(1, 60))
    elements.append(Paragraph(f"<b>Compliance Report</b>", styles['Title']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Document: {document_title}", styles['Heading2']))
    elements.append(Paragraph(f"Client ID: {client_id}", styles['Normal']))
    elements.append(Paragraph(f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", styles['Normal']))
    elements.append(Spacer(1, 40))
    
    score_style = ParagraphStyle('Score', parent=styles['Normal'], fontSize=48, textColor=border_color, alignment=1)
    elements.append(Paragraph(f"Score: {analysis_result.get('complianceScore', 0)}/100", score_style))
    elements.append(Paragraph(f"Risk Level: {overall_risk}", ParagraphStyle('Risk', parent=styles['Heading2'], alignment=1)))
    
    elements.append(PageBreak())
    
    # PAGE 2 - RISK SUMMARY
    elements.append(Paragraph("Risk Breakdown", styles['Heading1']))
    breakdown = analysis_result.get('riskBreakdown', {})
    
    chart_draw = Drawing(400, 200)
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = [[breakdown.get('high', 0), breakdown.get('medium', 0), breakdown.get('low', 0)]]
    bc.strokeColor = colors.white
    bc.valueAxis.valueMin = 0
    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.categoryNames = ['High', 'Medium', 'Low']
    bc.bars[0].fillColor = colors.HexColor('#E24B4A')
    chart_draw.add(bc)
    elements.append(chart_draw)
    
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Laws Applicable:", styles['Heading3']))
    elements.append(Paragraph(", ".join(analysis_result.get('lawsApplicable', [])), styles['Normal']))
    
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Overall Explanation", styles['Heading3']))
    elements.append(Paragraph(analysis_result.get('overallExplanation', ''), styles['Normal']))
    
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Overall Recommendation", styles['Heading3']))
    elements.append(Paragraph(analysis_result.get('overallRecommendation', ''), styles['Normal']))
    
    elements.append(PageBreak())
    
    # PAGE 3+ - CLAUSES
    elements.append(Paragraph("Clause Analysis", styles['Heading1']))
    elements.append(Spacer(1, 10))
    
    for clause in analysis_result.get('clauses', []):
        c_risk = clause.get('riskLevel', 'LOW').upper()
        c_border, c_bg = risk_colors.get(c_risk, risk_colors["LOW"])
        
        clause_content = [
            Paragraph(f"<b>Clause {clause.get('clauseNumber', '-')}</b> | Law: {clause.get('lawReference', 'N/A')}", styles['Heading4']),
            Spacer(1, 5),
            Paragraph(f"<i>{clause.get('text', '')}</i>", styles['Italic']),
            Spacer(1, 5),
            Paragraph(f"<b>Risk:</b> {clause.get('riskReason', '')}", styles['Normal']),
            Spacer(1, 5),
            Paragraph(f"<b>Recommendation:</b> {clause.get('recommendation', '')}", styles['Normal'])
        ]
        
        t = Table([[clause_content]], colWidths=[500])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), c_bg),
            ('LINEBEFORE', (0, 0), (0, -1), 4, c_border),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    # Build PDF and force GC
    doc.build(elements)
    buffer.seek(0)
    
    del doc
    del elements
    gc.collect()
    
    return buffer