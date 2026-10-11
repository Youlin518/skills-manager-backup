# -*- coding: utf-8 -*-
"""Replace figure placeholders in the manual with the generated schematic PNGs."""
import os, re, sys
sys.path.insert(0, 'D:/tmp/pylibs')
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

DOC = r'D:\git\zc\MS.ExamSystem\MS.ExamSystemV1.1_软件操作使用说明书.docx'
FIG_DIR = 'D:/tmp/figures'
OUT = r'D:\git\zc\MS.ExamSystem\MS.ExamSystemV1.1_软件操作使用说明书.docx'

PLACEHOLDER_RE = re.compile(r'【图\s+([^】]+?)\s+此处放置对应界面截图】')

def set_cjk(run, font='宋体'):
    run.font.name = font
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    rFonts.set(qn('w:eastAsia'), font)
    rFonts.set(qn('w:ascii'), font)
    rFonts.set(qn('w:hAnsi'), font)

def insert_before(parent, anchor, new_el):
    idx = list(parent).index(anchor)
    parent.insert(idx, new_el)

def replace_placeholder(paragraph, img_path, caption_text):
    """Return (image_para, caption_para) inserted before paragraph, then caller removes placeholder."""
    doc = paragraph.part.document
    # image paragraph (centered)
    img_p = doc.add_paragraph()
    img_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    img_p.paragraph_format.space_before = Pt(6)
    img_p.paragraph_format.space_after = Pt(4)
    run = img_p.add_run()
    run.add_picture(img_path, width=Cm(15))
    # caption paragraph (centered)
    cap_p = doc.add_paragraph()
    cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap_p.paragraph_format.space_after = Pt(10)
    run = cap_p.add_run(caption_text)
    run.italic = True
    run.font.size = Pt(9.5)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    set_cjk(run, '宋体')
    # move elements before the placeholder
    anchor = paragraph._element
    parent = anchor.getparent()
    insert_before(parent, anchor, img_p._element)
    insert_before(parent, anchor, cap_p._element)

def main():
    if not os.path.exists(DOC):
        raise FileNotFoundError(DOC)
    doc = Document(DOC)
    replaced = 0
    # iterate over a snapshot because we'll mutate the paragraph order
    for p in list(doc.paragraphs):
        text = p.text.strip()
        m = PLACEHOLDER_RE.search(text)
        if not m:
            continue
        caption = m.group(1).strip()
        fig_num = caption.split(maxsplit=1)[0]
        img_name = 'fig_' + fig_num.replace('-', '_') + '.png'
        img_path = os.path.join(FIG_DIR, img_name)
        if not os.path.exists(img_path):
            print('SKIP (missing file):', caption, '->', img_path)
            continue
        replace_placeholder(p, img_path, '图 ' + caption)
        p._element.getparent().remove(p._element)
        replaced += 1
        print('REPLACED:', caption, '->', img_path)

    # ensure output directory exists
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT)
    print('SAVED:', OUT, '| placeholders replaced:', replaced)

if __name__ == '__main__':
    main()
