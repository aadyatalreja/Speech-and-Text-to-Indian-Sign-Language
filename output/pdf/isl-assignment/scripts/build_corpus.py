import csv, json, unicodedata
from collections import Counter, defaultdict
from pathlib import Path
P=Path('output/pdf/isl-assignment')
ds=json.loads((P/'corpus.json').read_text(encoding='utf-8'))
ds[2]['title']='INCLUDE: A Large Scale Dataset for Indian Sign Language Recognition'
ds[2]['title_note']='Crossref short title expanded using the authors\' AI4Bharat publication record.'
def norm(a):
    return ''.join(c for c in unicodedata.normalize('NFKD',a) if not unicodedata.combining(c)).casefold().strip()
authors=defaultdict(list); names={}
for d in ds:
    for a in d['authors']:
        authors[norm(a)].append(d['id']); names[norm(a)]=a
links=[]; degree=Counter(); strength=Counter()
for i,a in enumerate(ds):
    for b in ds[i+1:]:
        shared=sorted(set(map(norm,a['authors'])) & set(map(norm,b['authors'])))
        if shared:
            links.append(dict(source_id=a['id'],target_id=b['id'],strength=len(shared),shared_authors='; '.join(names[s] for s in shared)))
            degree.update([a['id'],b['id']]); strength[a['id']]+=len(shared); strength[b['id']]+=len(shared)
for d in ds: d.update(degree=degree[d['id']],total_link_strength=strength[d['id']])
(P/'corpus.json').write_text(json.dumps(ds,ensure_ascii=False,indent=2),encoding='utf-8')
with (P/'ISL-25-papers.csv').open('w',newline='',encoding='utf-8-sig') as f:
    fields=['id','title','authors','year','doi','arxiv','url','venue','record_type','project_relevance','degree','total_link_strength','metadata_source','verified_on']
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader()
    for d in ds:w.writerow({**d,'authors':'; '.join(d['authors'])})
bib=[]
for d in ds:
    lines=[f'@misc{{isl{d["id"]:02},',f'  title = {{{d["title"]}}},',f'  author = {{{" and ".join(d["authors"])}}},',f'  year = {{{d["year"]}}},',f'  url = {{{d["url"]}}},']
    if d.get('doi'):lines.append(f'  doi = {{{d["doi"]}}},')
    if d.get('arxiv'):lines.extend([f'  eprint = {{{d["arxiv"]}}},','  archivePrefix = {arXiv},'])
    lines.append('}'); bib.append('\n'.join(lines))
(P/'ISL-25-papers.bib').write_text('\n\n'.join(bib),encoding='utf-8')
net={'network':{'items':[{'id':d['id'],'label':f'[{d["id"]:02}] {d["authors"][0].split()[-1]} {d["year"]}','description':d['title'],'url':d['url'],'weights':{'Links':d['degree'],'Total link strength':d['total_link_strength']},'scores':{'Year':d['year']}} for d in ds],'links':[{k:l[k] for k in ['source_id','target_id','strength']} for l in links]},'info':{'title':'Speech and Text to Indian Sign Language - 25-paper shared-authorship network','description':'Papers are nodes; links count shared authors. Not a citation network. Verified 3 November 2026.'},'config':{'parameters':{'largest_component':False,'attraction':2,'repulsion':1,'resolution':1,'min_cluster_size':1,'merge_small_clusters':True}}}
(P/'ISL-VOSviewer-network.json').write_text(json.dumps(net,ensure_ascii=False,indent=2),encoding='utf-8')
with (P/'shared-author-edges.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=['source_id','target_id','strength','shared_authors']);w.writeheader();w.writerows(links)
stats={'nodes':len(ds),'edges':len(links),'total_link_strength':sum(l['strength'] for l in links),'density':2*len(links)/(len(ds)*(len(ds)-1)),'mean_degree':2*len(links)/len(ds),'authors':[{'name':names[a],'papers':ids} for a,ids in sorted(authors.items(),key=lambda x:(-len(x[1]),x[0])) if len(ids)>1],'top_papers':sorted(ds,key=lambda d:(-d['degree'],-d['total_link_strength'],d['id']))[:5]}
(P/'network-statistics.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(stats,ensure_ascii=True,indent=2))
