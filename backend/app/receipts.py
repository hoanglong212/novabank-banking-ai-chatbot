"""Deterministic simulated receipts based on immutable transaction snapshots."""
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from .posting import VIETNAM

pdfmetrics.registerFont(TTFont('NovaSans', str(Path(__file__).parent / 'fonts' / 'NotoSans-Regular.ttf')))
INK, BRAND, MUTED = colors.HexColor('#1a1530'), colors.HexColor('#5b21b6'), colors.HexColor('#6b6785')


def receipt_pdf(tx: dict) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=48, leftMargin=48,
                            topMargin=48, bottomMargin=48, invariant=1,
                            title='NovaBank simulated transaction receipt', author='NovaBank Demo')
    text = ParagraphStyle('text', fontName='NovaSans', fontSize=10, leading=16, textColor=INK,
                          splitLongWords=True)
    muted = ParagraphStyle('muted', parent=text, fontSize=9, textColor=MUTED)
    heading = ParagraphStyle('heading', parent=text, fontSize=24, leading=32, textColor=BRAND)
    amount_style = ParagraphStyle('amount', parent=text, fontSize=27, leading=38)
    p = lambda value, style=text: Paragraph(escape(str(value)).replace('\n', '<br/>'), style)
    sign = '+' if tx['direction'] == 'in' else '-'
    story = [p('novabank', heading), p('SIMULATED TRANSACTION RECEIPT', muted), Spacer(1, 28),
             p(f'{sign}{tx["amount_vnd"]:,} VND', amount_style), p('Completed', muted), Spacer(1, 22),
             HRFlowable(width='100%', color=colors.HexColor('#ebe8f3')), Spacer(1, 14)]
    stamp = datetime.fromisoformat(tx['created_at']).astimezone(VIETNAM).strftime('%d %b %Y, %H:%M:%S')
    rows = [
        ('Transaction reference', tx['id']), ('Account holder', tx['holder_name']),
        ('Account', tx['account_id']), ('Direction', 'Incoming' if tx['direction'] == 'in' else 'Outgoing'),
        ('Recorded at (UTC+7)', stamp), ('Description', tx['description']),
    ]
    if tx['counterparty_account']:
        rows.extend([('Counterparty', tx['counterparty_name'] or 'Name not verified'),
                     ('Counterparty account', tx['counterparty_account']), ('Bank', tx['counterparty_bank'])])
    rows.extend([('Fee', f'{tx["fee_vnd"]:,} VND' if tx['fee_vnd'] is not None else 'Not recorded'),
                 ('Balance after transaction', f'{tx["balance_after_vnd"]:,} VND'
                  if tx['balance_after_vnd'] is not None else 'Not recorded for this older demo transaction')])
    table = Table([[p(label, muted), p(value)] for label, value in rows], colWidths=[155, A4[0] - 251])
    table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                               ('RIGHTPADDING', (0, 0), (-1, -1), 12), ('TOPPADDING', (0, 0), (-1, -1), 9),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
                               ('LINEBELOW', (0, 0), (-1, -1), .4, colors.HexColor('#ebe8f3'))]))
    story.extend([table, Spacer(1, 24), p('This receipt belongs to a fictional banking demonstration. '
                  'No real money was transferred. Keep the transaction reference for support.', muted)])
    doc.build(story)
    return output.getvalue()
