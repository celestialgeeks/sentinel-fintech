#!/usr/bin/env python3
"""Generate PDF report from combined markdown."""
import os
import markdown
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from html.parser import HTMLParser

# Register fonts
for fp, name in [
    ('/System/Library/Fonts/Helvetica.ttf', 'Helvetica'),
    ('/System/Library/Fonts/Helvetica-Bold.ttf', 'Helvetica-Bold'),
    ('/System/Library/Fonts/Supplemental/Georgia.ttf', 'Georgia'),
]:
    if os.path.exists(fp):
        try:
            pdfmetrics.registerFont(TTFont(name, fp))
        except: pass

with open('/Users/shreyashsingh/my info/projects/sentinel-fintech/docs/REPORT_Combined.md', 'r') as f:
    md_text = f.read()

html = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'toc'])

doc = SimpleDocTemplate(
    '/Users/shreyashsingh/my info/projects/sentinel-fintech/docs/REPORT_Sentinel.pdf',
    pagesize=A4,
    rightMargin=0.75*inch,
    leftMargin=0.75*inch,
    topMargin=0.75*inch,
    bottomMargin=0.75*inch
)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle('MyTitle', fontSize=22, alignment=1, spaceAfter=12, fontName='Helvetica-Bold'))
styles.add(ParagraphStyle('MyH1', fontSize=16, spaceBefore=14, spaceAfter=6, fontName='Helvetica-Bold'))
styles.add(ParagraphStyle('MyH2', fontSize=13, spaceBefore=12, spaceAfter=4, fontName='Helvetica-Bold'))
styles.add(ParagraphStyle('MyH3', fontSize=11, spaceBefore=10, spaceAfter=4, fontName='Helvetica-Bold'))
styles.add(ParagraphStyle('MyBody', fontSize=10, leading=14, spaceAfter=6, fontName='Helvetica'))
styles.add(ParagraphStyle('MyCode', fontSize=8, leading=10, fontName='Courier'))

class PDFBuilder(HTMLParser):
    def __init__(self, styles):
        super().__init__()
        self.styles = styles
        self.story = []
        self.in_code = False
        self.in_table = False
        self.current_text = []
        self.current_tag = None
        self.table_data = []
        self.current_row = []
        self.current_cell = []
        self.heading_level = 0
        self.para_buffer = []

    def handle_starttag(self, tag, attrs):
        if tag in ('h1','h2','h3','h4','h5','h6'):
            self.current_tag = tag
            self.current_text = []
            self.heading_level = int(tag[-1])
        elif tag == 'code':
            self.in_code = True
            self.current_text = []
        elif tag == 'pre':
            self.in_code = True
        elif tag == 'table':
            self.in_table = True
            self.table_data = []
        elif tag == 'tr':
            self.current_row = []
        elif tag in ('th','td'):
            self.current_cell = []
        elif tag == 'p' and not self.in_table:
            if self.current_text:
                self.para_buffer.append(''.join(self.current_text))
                self.current_text = []
        elif tag == 'br':
            if self.current_text:
                self.current_text.append('\n')
        elif tag == 'hr':
            self.story.append(Spacer(1, 12))
        elif tag == 'li':
            text = ''.join(self.current_text).strip()
            if text:
                self.story.append(Paragraph('\u2022 ' + text, self.styles['MyBody']))
                self.story.append(Spacer(1, 2))
            self.current_text = []

    def handle_endtag(self, tag):
        if tag in ('h1','h2','h3','h4','h5','h6'):
            text = ''.join(self.current_text).strip()
            if text:
                level = min(self.heading_level, 3)
                style_name = f'MyH{level}'
                self.story.append(Paragraph(text, self.styles[style_name]))
                self.story.append(Spacer(1, 6))
            self.current_text = []
        elif tag == 'code':
            text = ''.join(self.current_text).strip()
            if text:
                formatted = text.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')
                self.story.append(Paragraph(f'<pre>{formatted}</pre>', self.styles['MyCode']))
                self.story.append(Spacer(1, 6))
            self.current_text = []
            self.in_code = False
        elif tag == 'pre':
            self.in_code = False
        elif tag == 'tr':
            if self.current_cell:
                self.current_row.append(''.join(self.current_cell).strip())
            if self.current_row:
                self.table_data.append(self.current_row)
            self.current_row = []
        elif tag in ('th','td'):
            self.current_cell.append(''.join(self.current_cell).strip() if self.current_cell else '')
            self.current_cell = [''.join(self.current_cell).strip()]
        elif tag == 'table':
            if self.table_data:
                p_rows = [[Paragraph(c, self.styles['MyBody']) for c in row] for row in self.table_data]
                t = Table(p_rows, repeatRows=1)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8e8')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                self.story.append(t)
                self.story.append(Spacer(1, 12))
            self.in_table = False
        elif tag == 'p' and not self.in_table:
            for p_text in self.para_buffer:
                if p_text.strip():
                    self.story.append(Paragraph(p_text, self.styles['MyBody']))
                    self.story.append(Spacer(1, 4))
            self.para_buffer = []

    def handle_data(self, data):
        if self.current_tag:
            self.current_text.append(data)
        elif self.current_cell:
            self.current_cell.append(data)
        elif self.in_code:
            self.current_text.append(data)

parser = PDFBuilder(styles)
parser.feed(html)
story = parser.story
doc.build(story)
print(f"PDF generated: REPORT_Sentinel.pdf ({len(story)} elements)")
