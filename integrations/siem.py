"""Upload pre-generated fixtures to a configured SIEM; no network calls without --send."""
import argparse, json, os
from pathlib import Path
import requests
try: from .ctfd_import import validate_url
except ImportError: from ctfd_import import validate_url

def ingest(kind,url,token,path):
    url=validate_url(url)
    if kind=='elastic':
        r=requests.post(url+'/_bulk',data=Path(path).read_bytes(),headers={'Authorization':'ApiKey '+token,'Content-Type':'application/x-ndjson'},timeout=30,allow_redirects=False)
    else:
        r=requests.post(url+'/services/collector/event',data=Path(path).read_bytes(),headers={'Authorization':'Splunk '+token,'Content-Type':'application/json'},timeout=30,allow_redirects=False)
    r.raise_for_status(); data=r.json()
    if kind=='elastic' and data.get('errors') is not False: raise RuntimeError('Elasticsearch bulk response contains errors or lacks an acknowledgement. Inspect the server before retrying.')
    if kind=='splunk' and data.get('code')!=0: raise RuntimeError('Splunk HEC rejected the events.')
    return {'accepted_by_endpoint':True,'searchability_verified':False,'response':data}
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('kind',choices=['splunk','elastic']); p.add_argument('--url',required=True); p.add_argument('--send',action='store_true'); a=p.parse_args(); path=Path(__file__).parent/'package'/('splunk-hec.ndjson' if a.kind=='splunk' else 'elastic-bulk.ndjson')
    if not a.send: print(json.dumps({'mode':'dry-run','url':a.url,'bytes':path.stat().st_size,'network_requests':0}))
    else:
        token=os.getenv('SIEM_TOKEN')
        if not token: p.error('Set SIEM_TOKEN.')
        print(json.dumps(ingest(a.kind,a.url,token,path)))
