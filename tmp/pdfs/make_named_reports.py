from pathlib import Path
import re
from pypdf import PdfReader
from PIL import Image

source = Path('tmp/pdfs/make_report.py').read_text(encoding='utf-8')
people = [
    ('Aadya Arun Talreja', '1RVU23CSE003', 'Aadya-Arun-Talreja'),
    ('Ananya N Shetty', '1RVU23CSE051', 'Ananya-N-Shetty'),
    ('Aisiri Masthi', '1RVU23CSE032', 'Aisiri-Masthi'),
]
base = Path('output/pdf/isl-assignment')
original = base / 'RM-Assignment-2-Speech-Text-to-ISL-Prajna-MS.pdf'
def text(path):
    return re.sub(r'\s+', ' ', ' '.join(p.extract_text() for p in PdfReader(path).pages)).strip()
expected = text(original)
previews = []
for name, usn, slug in people:
    script = source.replace('Prajna M S', name).replace('1RVU23CSE340', usn)
    script = script.replace('RM-Assignment-2-Speech-Text-to-ISL-Prajna-MS.pdf', f'RM-Assignment-2-Speech-Text-to-ISL-{slug}.pdf')
    script = script.replace("(P/'Assignment-editable.md').write_text", f"(P/'Assignment-{slug}-editable.md').write_text")
    script = script.replace("Path('tmp/pdfs/report-render')", f"Path('tmp/pdfs/report-render-{slug}')")
    exec(compile(script, f'<report-{slug}>', 'exec'), {'__name__': '__main__'})
    output = base / f'RM-Assignment-2-Speech-Text-to-ISL-{slug}.pdf'
    actual = text(output).replace(name, 'Prajna M S').replace(usn, '1RVU23CSE340')
    assert actual == expected, f'Unexpected content change: {name}'
    assert len(PdfReader(output).pages) == 7
    assert PdfReader(output).metadata.author == name
    previews.append(Image.open(f'tmp/pdfs/report-render-{slug}/page-01.png').convert('RGB'))
    print('VERIFIED', name, usn, output.resolve())
sheet = Image.new('RGB', (previews[0].width * 3, previews[0].height), '#dde5eb')
for i, im in enumerate(previews): sheet.paste(im, (i * im.width, 0))
sheet.save('tmp/pdfs/three-names-preview.png')
