import json, sys
from datetime import datetime
from pathlib import Path

def validate(path):
    cases=json.loads(Path(path).read_text()); seen=set()
    for c in cases:
        assert c['id'] not in seen, 'Duplicate case ID'; seen.add(c['id'])
        assert len(c['questions'])==3, 'This range uses three findings per case'
        for k in ('title','brief','writeup'):
            assert all(c[k].get(lang) for lang in ('en','ms')), f'Missing translation: {k}'
        ids=set()
        for row in c['logs']:
            assert row['id'] not in ids, 'Duplicate event ID'; ids.add(row['id']); datetime.fromisoformat(row['timestamp'])
            assert set(row)=={'id','timestamp','host','event','user','source_ip','detail'}, 'Incorrect event schema'
        for i,q in enumerate(c['questions']):
            assert q['id']==f'q{i+1}' and q['points']==50 and q['answers'], 'Invalid finding schema'
            for k in ('prompt','explanation'): assert all(q[k].get(lang) for lang in ('en','ms'))
        assert len(c['hints'])==2 and all(all(h.get(lang) for lang in ('en','ms')) for h in c['hints'])
        assert 'synthetic' in c['provenance'].lower(), 'Declare dataset provenance'
    return {'cases':len(cases),'events':sum(len(c['logs']) for c in cases),'questions':sum(len(c['questions']) for c in cases)}
if __name__=='__main__': print(json.dumps(validate(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'data/cases.json')))
