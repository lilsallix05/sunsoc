"""Build a portable CTFd API import package and SIEM-ready synthetic datasets."""
import csv, io, json, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def build(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    cases=json.loads((ROOT/'data/cases.json').read_text()); manifest=[]; hec=[]; bulk=[]
    for c in cases:
        buf=io.StringIO(); writer=csv.DictWriter(buf,fieldnames=c['logs'][0].keys()); writer.writeheader(); writer.writerows(c['logs']); (out/f'{c["id"]}.csv').write_text(buf.getvalue())
        for row in c['logs']:
            event={**row,'case_id':c['id'],'synthetic':True,'@timestamp':row['timestamp']}
            from datetime import datetime
            hec.append({'time':datetime.fromisoformat(row['timestamp']).timestamp(),'host':row['host'],'sourcetype':'sunsoc:synthetic','source':c['id'],'event':event})
            bulk.extend([{'index':{'_index':'sunsoc-training','_id':row['id']}},event])
        for q in c['questions']:
            manifest.append({'key':c['id']+'-'+q['id'],'challenge':{'name':f'SunSOC / {c["title"]["en"]} / {q["id"]}','category':c['source'],'description':f'{c["brief"]["en"]}\n\n{q["prompt"]["en"]}\n\nBahasa Melayu:\n{c["brief"]["ms"]}\n\n{q["prompt"]["ms"]}\n\nOriginal synthetic evidence. Submit the literal answer (case insensitive).','value':50,'type':'standard','state':'hidden','max_attempts':0},'flags':[{'content':a,'type':'static','data':'case_insensitive'} for a in q['answers']],'hints':[{'content':h['en']+'\n\n'+h['ms'],'cost':10} for h in c['hints']],'file':c['id']+'.csv'})
    (out/'manifest.json').write_text(json.dumps({'schema_version':1,'format':'SunSOC CTFd REST import, not a native CTFd backup','challenges':manifest},ensure_ascii=False,indent=2))
    (out/'splunk-hec.ndjson').write_text(''.join(json.dumps(r)+'\n' for r in hec))
    (out/'elastic-bulk.ndjson').write_text(''.join(json.dumps(r)+'\n' for r in bulk))
    (out/'README.txt').write_text('Private instructor package: contains answers. Import with integrations/ctfd_import.py. Never serve this folder publicly. Each finding becomes a separate 50-point CTFd challenge. Hints cost 10 per finding in CTFd, unlike per case in the native range. All challenges stay hidden until the operator reviews and releases them.\n')
    with zipfile.ZipFile(out/'sunsoc-ctfd-package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.iterdir()):
            if p.suffix in ('.json','.csv','.txt'): z.write(p,p.name)
    return {'cases':len(cases),'events':len(hec),'ctfd_challenges':len(manifest)}
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--output',default=str(ROOT/'integrations/package')); a=p.parse_args(); print(json.dumps(build(a.output)))
