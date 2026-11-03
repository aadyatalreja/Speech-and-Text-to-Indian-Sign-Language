import json, re, html, zipfile
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pypdfium2 as pdfium
from PIL import Image as PILImage, ImageOps, ImageDraw

P=Path('output/pdf/isl-assignment'); ds=json.loads((P/'corpus.json').read_text(encoding='utf-8'))
S=json.loads((P/'network-statistics.json').read_text(encoding='utf-8'))
font=Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('Body',str(font/'arial.ttf')))
pdfmetrics.registerFont(TTFont('BodyBold',str(font/'arialbd.ttf')))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold',italic='Body',boldItalic='BodyBold')
styles=getSampleStyleSheet()
for name in ['Normal','BodyText']: styles[name].fontName='Body'; styles[name].fontSize=10; styles[name].leading=14
styles.add(ParagraphStyle(name='TitleCustom',fontName='BodyBold',fontSize=23,leading=28,textColor=colors.HexColor('#12354b'),spaceAfter=16))
styles.add(ParagraphStyle(name='Sub',fontName='BodyBold',fontSize=13,leading=18,textColor=colors.HexColor('#147d86'),spaceBefore=14,spaceAfter=8))
styles.add(ParagraphStyle(name='SmallCustom',fontName='Body',fontSize=8.4,leading=12,textColor=colors.HexColor('#455566'),spaceAfter=8))
styles.add(ParagraphStyle(name='RefCustom',fontName='Body',fontSize=8.8,leading=12.5,spaceAfter=12))
styles['Normal'].spaceAfter=9
story=[]; md=[]
def para(t,style='Normal'):
    story.append(Paragraph(t,styles[style])); md.append(re.sub('<[^>]+>','',t))
def heading(t):para(t,'Sub')
def table(rows,widths):
    data=[[Paragraph(str(x),styles['SmallCustom']) for x in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8f1f5')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#8eb3bd')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#d5dfe4')),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.append(t);md.extend([' | '.join(map(str,r)) for r in rows])
def image(name,maxheight=300):
    f=P/name; im=PILImage.open(f); w,h=im.size; scale=min(491/w,maxheight/h)
    story.append(Image(str(f),width=w*scale,height=h*scale));md.append(f'![{name}]({name})')
def page():story.append(PageBreak());md.append('\n---\n')

para('RESEARCH METHODOLOGY','SmallCustom')
para('Assignment 2<br/>Speech and Text to<br/>Indian Sign Language','TitleCustom')
para('<b>Name:</b> Prajna M S &nbsp;&nbsp; <b>USN:</b> 1RVU23CSE340')
para('Literature mapping and research-network analysis | 3 November 2026','SmallCustom')
heading('1. Aim and scope')
para('To examine the literature and collaboration structure relevant to SignAI, our experimental English speech/text-to-Indian Sign Language (ISL) playback project. The corpus connects ISL grammar and gloss conversion, data resources, continuous sign production, non-manual features, and human evaluation. Eight papers directly concern ISL [1-8]; the remaining seventeen provide comparative methods and research context [9-25].')
heading('2. Project context')
para('The current prototype accepts English text or browser speech transcription, constructs a gloss sequence, resolves signs from a repository, and plays available signer videos or avatar clips. Its draft grammar, demonstration assets, and spelling fallbacks require ISL signer review. This assignment maps research that can guide development; it does not establish the linguistic accuracy of the prototype.')
heading('3. Corpus selection and verification')
para('A purposive corpus of 25 distinct research works was assembled from arXiv, ACL Anthology, CVF, and publisher/Crossref records. Titles, complete author lists, dates, and persistent links were checked on 3 November 2026. Inclusion required direct relevance to ISL or a clear connection to translation, pose generation, co-articulation, resources, or evaluation. Generic machine-translation papers and alphabet-only recognition demonstrations were excluded.')
para('References use the year of the cited record: initial arXiv submission for arXiv records and publication metadata for DOI records. A conference version may have a later year. For example, SignLLM is cited as a 2024 preprint here, while ResearchRabbit indexes a 2025 workshop version. The set includes conference papers, journal articles, reviews, and preprint records; it is not described as 25 journal articles. It is a focused sample, not a systematic or exhaustive review.','SmallCustom')

page();heading('4. VOSviewer bibliographic network')
image('VOSviewer-full-network.jpg',300)
para('Figure 1. Genuine VOSviewer Online screenshot of the full 25-paper shared-authorship network. The application reports 25 items, 43 links, total link strength 112, and 13 clusters. Numeric labels refer to the bibliography. Some labels overlap within the tightly connected production group.','SmallCustom')
para('<b>Network definition.</b> Each node is a paper. An undirected edge exists when two papers share at least one author; edge strength is the number of shared authors. Full names are normalized for case and diacritics; surnames alone are never matched. The edge list is derived from the verified corpus and imported as VOSviewer JSON without preset coordinates or clusters. These are collaboration-proximity links, not citations, co-citations, or bibliographic coupling.')
para('<b>Settings.</b> Association-strength normalization; attraction 2; repulsion -1 for readable separation; clustering resolution 1; minimum cluster size 1; merging of small clusters enabled. All papers, including isolates, are retained. Node size uses the number of links. VOSviewer computed the layout and clusters. No citation counts were supplied.')
table([['Measure','Calculation / result'],['Binary density','D = 2E / [N(N - 1)] = 86 / 600 = 0.1433 = 14.33%'],['Mean degree','2E / N = 86 / 25 = 3.44'],['Weighted edge total','112 shared-author units across 43 edges'],['Highest paper degree','[19] and [20]: 9 neighbours each; weighted strength 19 each']],[135,356])
para('The density calculation counts each edge once, irrespective of how many authors are shared. Weighted strength is a separate quantity. Thirteen clusters include single-paper groups; clusters must not be interpreted automatically as thirteen research themes.','SmallCustom')

page();heading('5. ResearchRabbit paper-connection graph')
image('ResearchRabbit-graph.jpg',330)
para('Figure 2. Genuine ResearchRabbit graph from the assignment collection and a Similar articles search. Search inputs and retrieved results are distinguished by the application legend; directed reference arrows describe ResearchRabbit relationships.','SmallCustom')
para('<b>Workflow.</b> The 25-record BibTeX file was submitted for import. Automatically resolved records were checked against the saved collection. Two unrelated saved-record substitutions were removed from the assignment collection; How2Sign and the existing ISL gloss-conversion and systematic-review records were added individually. The final collection contains 23 verified corpus works. Papers [13] and [15] were not among the 23 saved search inputs. Paper [15] subsequently appears among the related search results. Both remain in the full 25-paper bibliography and VOSviewer network.')
para('<b>Coverage and interpretation.</b> A Similar articles search was run from this 23-paper collection, requesting 20 results. The displayed map contains input records and retrieved neighbours, so its node count is not the size of the verified corpus. ResearchRabbit can index conference and preprint versions separately and can display publication years that differ from the cited arXiv records. No citation-density or global influence ranking is inferred from the picture.')
para('<b>Reading the map.</b> The graph provides a reading route between ISL-specific work, sign-generation research, and related translation resources. It complements Figure 1 because reference relationships can connect papers written by entirely different teams. The VOSviewer density and author counts are calculated only from the reproducible 25-paper shared-authorship data, not from this expanded graph.')

page();heading('6. Influential contribution and connected authors')
para('<b>Selected foundational production paper:</b> Saunders, Camgoz, and Bowden (2020), <i>Progressive Transformers for End-to-End Sign Language Production</i> [9]. Its text-to-continuous-pose formulation, variable-length generation, and back-translation evaluation make it a useful methodological foundation for the project. This is a reasoned selection based on task relevance; it is not a claim that the paper has the highest citation count.')
para('<b>Most connected papers:</b> Neural Sign Language Translation [19] and Sign Language Transformers [20] each connect to nine corpus papers. Seven Saunders-led production works [9-15] each connect to eight papers and have weighted strength 22. These values measure shared-author overlap; they do not rank translation quality or scholarly impact.')
table([['Author(s)','Corpus papers','Reference numbers'],['Necati Cihan Camgoz; Richard Bowden','9 each','[9-15], [19], [20]'],['Ben Saunders','7','[9-15]'],['Suvajit Patra; Arkadip Maitra; Soumitra Samanta','3 each','[6-8]'],['Oscar Koller','3','[17], [19], [20]'],['Abhinav Joshi; Ashutosh Modi','2 each','[4], [5]'],['Kayo Yin; Amit Moryossef; Yoav Goldberg','2 each','[18], [21]']],[250,75,166])
heading('7. Network analysis (200-300 words)')
analysis=[
'The 25-paper corpus connects Indian Sign Language resources and grammar-based conversion with continuous sign production, multimodal animation, and evaluation. Eight works directly address ISL, while the other papers supply comparative methods and broader linguistic context. This balance supports the project without treating German or American Sign Language results as evidence of ISL accuracy.',
'The VOSviewer graph represents papers as nodes and shared authors as weighted links. Its 43 links yield a density of 14.33% and a mean degree of 3.44. The strongest collaborative region contains the Saunders, Camgoz, and Bowden production series. Camgoz and Bowden each occur in nine selected works. Neural Sign Language Translation and Sign Language Transformers each have nine neighbouring papers, whereas the seven Saunders-led production papers each have eight.',
'A separate ISL collaboration joins Patra, Maitra, and Samanta across recognition resources and continuous production. Joshi and Modi connect ISLTranslate with iSign. Yin, Moryossef, and Goldberg link linguistic inclusion with low-resource gloss translation. These groupings reflect shared research teams rather than automatically extracted topics. VOSviewer reports thirteen clusters, including isolated papers.',
'ResearchRabbit complements this structure through a reference graph generated from twenty-three resolved corpus works and related search results. It supports literature discovery across teams; its expanded nodes must not be used in the VOSviewer density calculation.',
'Progressive Transformers is selected as a foundational production contribution because it addresses continuous text-to-pose generation. For our project, the literature motivates reviewed ISL glosses, licensed assets, co-articulation, non-manual expression, and Deaf-signer comprehension testing. Smooth playback and successful software tests alone cannot demonstrate linguistic correctness.'
]
for a in analysis:para(a)
assert 200<=len(' '.join(analysis).split())<=300

page();heading('8. Implications for our project')
table([['Project component','Literature connection and proposed next step'],['English speech/text to gloss','[1], [2], [18]: review English-to-ISL transformations with ISL signers; preserve meaning and non-manual information. Speech transcription errors should be evaluated separately.'],['Repository and data','[3-6], [16]: compare vocabulary and continuous-pair resources. Confirm usage terms, signer consent, and attribution before ingesting recordings. Recognition datasets do not automatically provide sentence-level production targets.'],['Avatar and video playback','[7-15], [22]: study continuous motion, timing, handshape fidelity, transitions, and facial/body channels. Interpolated clips require comprehension review.'],['Evaluation','[9], [11], [14], [17]: combine held-out examples and diagnostic automatic measures with native ISL signer comprehension and acceptability studies. Back-translation scores depend on the reverse model.'],['Project evidence','The current repository describes an experimental prototype with demo assets and unverified grammar. Report software checks separately from signer-reviewed linguistic evaluation; do not transfer published model scores to this system.']],[145,346])
heading('9. Evidence and reproducibility')
table([['Assignment element','Evidence supplied'],['At least 25 genuine papers','25 verified bibliographic records with primary/registration links'],['VOSviewer network screenshot','Actual 25-item application screenshot; 43 reproducible edges'],['ResearchRabbit graph','Actual graph from 23 resolved corpus works plus related results; two unresolved records explicitly disclosed'],['Influence and author connections','Conceptual paper selection separated from measured degree and author occurrence'],['Network analysis','A 200-300 word analysis, with counts calculated from the exported edge list']],[180,311])
para('Supporting files: ISL-25-papers.csv, ISL-25-papers.bib, corpus.json, shared-author-edges.csv, network-statistics.json, ISL-VOSviewer-network.json, and the application screenshots. The input JSON permits VOSviewer to compute a new layout; screenshots preserve the observed session. The editable report text is supplied separately.','SmallCustom')
para('Software: <link href="https://app.vosviewer.com/" color="#147d86">VOSviewer Online</link>; <link href="https://app.vosviewer.com/docs/file-types/json-file-type/" color="#147d86">VOSviewer JSON specification</link>; <link href="https://app.researchrabbit.ai/library/collection/efd67acf-4efe-49aa-8637-d6cce67b26d9" color="#147d86">ResearchRabbit assignment collection</link>. Bibliography metadata: arXiv, ACL Anthology, CVF, and Crossref DOI registration records. INCLUDE\'s short Crossref title was expanded using the authors\' AI4Bharat publication record.','SmallCustom')

page();heading('10. References - verified research corpus')
para('Records are numbered consistently across the corpus and VOSviewer labels. Full author lists are retained in the CSV, BibTeX, and JSON files. Preprint-record years are distinguished from later proceedings versions.','SmallCustom')
for d in ds:
    a=', '.join(d['authors'][:3])+(' et al.' if len(d['authors'])>3 else '')
    ident=('arXiv:'+d['arxiv']) if d.get('arxiv') else ('DOI: '+d['doi'] if d.get('doi') else d['venue'])
    txt=f'[{d["id"]}] {html.escape(a)} ({d["year"]}). <b>{html.escape(d["title"])}</b>. {html.escape(ident)}.<br/><link href="{html.escape(d["url"])}" color="#147d86">{html.escape(d["url"])}</link>'
    story.append(KeepTogether([Paragraph(txt,styles['RefCustom'])]))
    md.append(f'[{d["id"]}] {a} ({d["year"]}). {d["title"]}. {ident}. {d["url"]}')
def footer(c,doc):
    c.setStrokeColor(colors.HexColor('#147d86')); c.setLineWidth(.7);c.line(52,43,543,43)
    c.setFont('Body',8);c.setFillColor(colors.HexColor('#657585'));c.drawString(52,29,'RESEARCH METHODOLOGY | Speech and Text to ISL');c.drawRightString(543,29,str(doc.page))
out=P/'RM-Assignment-2-Speech-Text-to-ISL-Prajna-MS.pdf'
doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=52,leftMargin=52,topMargin=42,bottomMargin=58,title='Research Methodology Assignment 2 - Speech and Text to Indian Sign Language',author='Prajna M S')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
(P/'Assignment-editable.md').write_text('\n\n'.join(md),encoding='utf-8')
renders=Path('tmp/pdfs/report-render');renders.mkdir(parents=True,exist_ok=True)
pdf=pdfium.PdfDocument(str(out)); thumbs=[]
for n,p in enumerate(pdf):
    im=p.render(scale=1.25).to_pil();im.save(renders/f'page-{n+1:02}.png'); t=im.copy();t.thumbnail((298,421)); thumbs.append(t)
sheet=PILImage.new('RGB',(3*318,((len(thumbs)+2)//3)*451),'#dbe3e8')
for i,im in enumerate(thumbs):sheet.paste(im,((i%3)*318+10,(i//3)*451+10))
sheet.save(renders/'contact-sheet.png')
print('PDF',out.resolve(),'PAGES',len(pdf),'ANALYSIS_WORDS',len(' '.join(analysis).split()))
