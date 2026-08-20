#!/usr/bin/env python3
"""Generate PDF report from combined markdown."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register fonts
for fp, name in [
    ('/System/Library/Fonts/Helvetica.ttf', 'Helvetica'),
    ('/System/Library/Fonts/Helvetica-Bold.ttf', 'Helvetica-Bold'),
    ('/System/Library/Fonts/Supplemental/Georgia.ttf', 'Georgia'),
]:
    if os.path.exists(fp):
        try:
            pdfmetrics.registerFont(TTFont(name, fp))
        except:
            pass

doc = SimpleDocTemplate(
    '/Users/shreyashsingh/my info/projects/sentinel-fintech/docs/REPORT_Sentinel.pdf',
    pagesize=A4,
    rightMargin=0.75*inch,
    leftMargin=0.75*inch,
    topMargin=0.75*inch,
    bottomMargin=0.75*inch
)

styles = getSampleStyleSheet()
story = []

with open('/Users/shreyashsingh/my info/projects/sentinel-fintech/docs/REPORT_Combined.md') as f:
    lines = f.readlines()

i = 0
while i < len(lines):
    line = lines[i].rstrip('\n')

    # Skip empty lines
    if not line.strip():
        story.append(Spacer(1, 6))
        i += 1
        continue

    # Horizontal rules
    if line.strip() == '---':
        story.append(Spacer(1, 12))
        i += 1
        continue

    # Headings
    if line.startswith('# '):
        story.append(Paragraph(line[2:], styles['Title']))
        story.append(Spacer(1, 8))
        i += 1
        continue
    if line.startswith('## '):
        story.append(Paragraph(line[3:], styles['Heading1']))
        story.append(Spacer(1, 6))
        i += 1
        continue
    if line.startswith('### '):
        story.append(Paragraph(line[4:], styles['Heading2']))
        story.append(Spacer(1, 4))
        i += 1
        continue
    if line.startswith('#### '):
        story.append(Paragraph(line[5:], styles['Heading3']))
        story.append(Spacer(1, 4))
        i += 1
        continue

    # Code blocks
    if line.startswith('```'):
        code_lines = []
        i += 1
        while i < len(lines) and not lines[i].strip().startswith('```'):
            code_lines.append(lines[i].rstrip())
            i += 1
        code_text = '\n'.join(code_lines)
        story.append(Paragraph(f'<pre>{code_text}</pre>', styles['Code']))
        story.append(Spacer(1, 6))
        i += 1
        continue

    # Tables
    if line.startswith('|'):
        table_rows = []
        while i < len(lines) and lines[i].strip().startswith('|'):
            row_line = lines[i].strip()
            if row_line.startswith('|---'):
                i += 1
                continue
            cells = [c.strip() for c in row_line.split('|')[1:-1]]
            table_rows.append(cells)
            i += 1
        if table_rows:
            p_rows = [[Paragraph(c, styles['Normal']) for c in row] for row in table_rows]
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
            story.append(t)
            story.append(Spacer(1, 12))
        continue

    # Bullet points
    if line.startswith('- '):
        story.append(Paragraph('\u2022 ' + line[2:], styles['Normal']))
        i += 1
        continue

    # Blockquotes
    if line.startswith('> '):
        story.append(Paragraph('<i>' + line[2:] + '</i>', styles['Normal']))
        i += 1
        continue

    # Regular paragraphs
    text = line.strip()
    if text:
        story.append(Paragraph(text, styles['Normal']))

    i += 1

doc.build(story)
print(f"PDF generated: REPORT_Sentinel.pdf ({len(story)} elements)")
