import concurrent.futures, html, json, re, urllib.request
from html.parser import HTMLParser
from pathlib import Path

OUT = Path('output/pdf/isl-assignment')
OUT.mkdir(parents=True, exist_ok=True)
class Meta(HTMLParser):
    def __init__(self): super().__init__(); self.m = {}
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta' and a.get('name','').startswith('citation_'):
            self.m.setdefault(a['name'], []).append(a.get('content',''))

records = [
('doi','10.1145/3384202','ISL grammar and avatar generation'),
('doi','10.1007/978-981-19-3951-8_55','English-to-ISL gloss conversion'),
('doi','10.1145/3394171.3413528','ISL isolated-sign dataset; resource context'),
('arxiv','2307.05440','ISL continuous translation dataset; reverse-direction resource'),
('arxiv','2407.05404','ISL benchmark including text-to-pose'),
('arxiv','2407.14224','ISL isolated-sign dataset and pose modelling'),
('doi','10.1109/ICSCC66177.2025.11233467','Continuous ISL production and co-articulation'),
('doi','10.24963/ijcai.2026/823','Gloss-driven ISL production with discrete pose representations'),
('arxiv','2004.14874','Continuous text-to-pose production'),
('arxiv','2008.12405','Manual and non-manual sign production'),
('arxiv','2103.06982','Continuous multi-channel production and evaluation'),
('arxiv','2107.11317','Motion primitives for sign animation'),
('arxiv','2112.05277','Skeleton structure in pose generation'),
('arxiv','2203.15354','Dictionary-sign co-articulation and video generation'),
('arxiv','2011.09846','Photo-realistic sign video production'),
('arxiv','2008.08143','Continuous ASL multimodal corpus; comparative resource'),
('arxiv','1908.08597','Interdisciplinary design and Deaf-community participation'),
('arxiv','2105.05222','Linguistically informed sign language processing'),
('url','https://openaccess.thecvf.com/content_cvpr_2018/html/Camgoz_Neural_Sign_Language_CVPR_2018_paper.html','Neural translation and reverse-direction evaluation'),
('arxiv','2003.13830','Joint recognition and translation; back-translation context'),
('url','https://aclanthology.org/2021.mtsummit-at4ssl.1/','Low-resource gloss translation and synthetic data'),
('url','https://aclanthology.org/2024.lrec-main.1022/','Multi-channel spatio-temporal production'),
('arxiv','2405.10718','Multilingual prompt-conditioned sign production'),
('doi','10.1016/j.eswa.2023.122846','Survey of sign language production'),
('doi','10.1007/s10209-021-00823-1','Systematic review of text-to-sign translation'),
]
def get(url):
    req=urllib.request.Request(url, headers={'User-Agent':'Academic bibliography verification/1.0'})
    return urllib.request.urlopen(req,timeout=45).read().decode('utf-8')
def collect(row):
    idx,(kind,key,role)=row; cache=OUT/f'source-{idx:02}.json'
    if cache.exists(): return json.loads(cache.read_text(encoding='utf-8'))
    if kind=='doi':
        raw=json.loads(get('https://api.crossref.org/works/'+key))['message']
        title=html.unescape(re.sub('<[^>]+>','',raw['title'][0]))
        authors=[' '.join(filter(None,[a.get('given'),a.get('family')])) for a in raw['author']]
        date=raw.get('published',raw.get('issued'))['date-parts'][0]
        d=dict(id=idx,title=title,authors=authors,year=date[0],url='https://doi.org/'+key,doi=key,venue='; '.join(raw.get('container-title',[])),record_type=raw.get('type'),metadata_source='https://api.crossref.org/works/'+key)
    else:
        url='https://arxiv.org/abs/'+key if kind=='arxiv' else key
        page=get(url); p=Meta(); p.feed(page); m=p.m
        title=m['citation_title'][0]; authors=m['citation_author']
        date=m.get('citation_publication_date',m.get('citation_date',['']))[0]
        year=int(re.search(r'20\d\d',date).group()) if re.search(r'20\d\d',date) else 2000+int(key[:2])
        # Canonicalize publisher "family, given" formatting for author matching.
        authors=[' '.join(a.split(', ')[::-1]) if ', ' in a else a for a in authors]
        d=dict(id=idx,title=title,authors=authors,year=year,url=url,doi=m.get('citation_doi',[''])[0],venue=m.get('citation_conference_title',m.get('citation_journal_title',['arXiv preprint' if kind=='arxiv' else 'Proceedings']))[0],record_type='preprint record' if kind=='arxiv' else 'conference paper',metadata_source=url)
        if kind=='arxiv': d['arxiv']=key
    d.update(project_relevance=role,verified_on='2026-11-03')
    cache.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    return d
if __name__=='__main__':
    result=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(collect,x):x[0] for x in enumerate(records,1)}
        for f in concurrent.futures.as_completed(futures):
            try:
                d=f.result(); result.append(d); print(d['id'],d['title'].encode('ascii','replace').decode(),flush=True)
            except Exception as e: print('FAILED',futures[f],str(e),flush=True)
    result.sort(key=lambda d:d['id'])
    (OUT/'corpus.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('COUNT',len(result))
