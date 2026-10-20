"""Import via CTFd's admin REST API. Default is dry-run; --send mutates a configured instance."""
import argparse, json, os
from pathlib import Path
from urllib.parse import urlparse
import requests

def validate_url(url):
    parsed=urlparse(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Provide a base HTTP(S) URL without credentials, query or fragment.')
    if parsed.scheme!='https' and parsed.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('Remote integrations require HTTPS.')
    return url.rstrip('/')

def send(package,url,token,state_file):
    url=validate_url(url); package=Path(package); state_file=Path(state_file)
    manifest=json.loads((package/'manifest.json').read_text()); state=json.loads(state_file.read_text()) if state_file.exists() else {'url':url,'items':{}}
    if state['url']!=url: raise ValueError('State belongs to another CTFd instance.')
    client=requests.Session(); client.headers['Authorization']='Token '+token
    def call(method,path,**kwargs):
        r=client.request(method,url+'/api/v1/'+path,timeout=30,allow_redirects=False,**kwargs); r.raise_for_status(); data=r.json()
        if data.get('success') is not True: raise RuntimeError(f'CTFd {path} rejected the request')
        return data['data']
    def save():
        state_file.parent.mkdir(parents=True,exist_ok=True); tmp=state_file.with_suffix('.tmp'); tmp.write_text(json.dumps(state,indent=2)); tmp.replace(state_file)
    existing=call('GET','challenges?view=admin')
    known={r['name']:r['id'] for r in existing}
    for item in manifest['challenges']:
        key=item['key']; record=state['items'].get(key)
        if not record:
            if item['challenge']['name'] in known: raise RuntimeError('A same-name challenge exists without a local receipt. Reconcile it manually before importing.')
            result=call('POST','challenges',json=item['challenge']); record={'id':result['id'],'flags':0,'hints':0,'file':False}; state['items'][key]=record; save()
        for flag in item['flags'][record['flags']:]:
            call('POST','flags',json={**flag,'challenge_id':record['id']}); record['flags']+=1; save()
        for hint in item['hints'][record['hints']:]:
            call('POST','hints',json={**hint,'challenge_id':record['id']}); record['hints']+=1; save()
        if not record['file']:
            with (package/item['file']).open('rb') as f: call('POST','files',data={'type':'challenge','challenge_id':record['id']},files={'file':(item['file'],f,'text/csv')})
            record['file']=True; save()
    return {'imported':len(state['items']),'state':'hidden; review in CTFd admin before release'}

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--package',default=str(Path(__file__).parent/'package')); p.add_argument('--url',default=os.getenv('CTFD_URL','http://127.0.0.1:8000')); p.add_argument('--state',default=str(Path(__file__).parent/'import-state.json')); p.add_argument('--send',action='store_true'); a=p.parse_args()
    if not a.send: print(json.dumps({'mode':'dry-run','url':a.url,'challenges':len(json.loads((Path(a.package)/'manifest.json').read_text())['challenges']),'network_requests':0}))
    else:
        token=os.environ.get('CTFD_TOKEN')
        if not token: p.error('Set CTFD_TOKEN in the environment.')
        print(json.dumps(send(a.package,a.url,token,a.state)))
