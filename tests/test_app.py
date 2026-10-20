import unittest, tempfile
from pathlib import Path
from app import create_app

class RangeTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=create_app({'TESTING':True,'DATABASE':str(Path(self.tmp.name)/'test.db'),'SECRET_KEY':'test-only','FACILITATOR_TOKEN':'local-test-token'})
        self.client=self.app.test_client()
        self.csrf=self.client.get('/api/session').json['csrf']
    def tearDown(self): self.tmp.cleanup()
    def post(self,path,data): return self.client.post(path,json=data,headers={'X-CSRF-Token':self.csrf})
    def register(self,name='analyst'):
        r=self.post('/api/register',{'name':name,'password':'long-password-123'})
        self.assertEqual(r.status_code,201,r.json); self.csrf=r.json['csrf']
    def test_protected_content_and_csrf(self):
        self.assertEqual(self.client.post('/api/register',json={}).status_code,403)
        self.assertEqual(self.client.get('/api/cases/mailroom').status_code,401)
        self.assertEqual(self.client.get('/api/facilitator').status_code,403)
    def test_scoring_hint_idempotency_and_no_answer_leak(self):
        self.register()
        cases=self.client.get('/api/cases').json
        self.assertEqual(len(cases),8)
        case=self.client.get('/api/cases/mailroom').json
        self.assertNotIn('answers',str(case)); self.assertNotIn('writeup',case)
        self.assertEqual(self.post('/api/cases/mailroom/hint',{}).json['cost'],10)
        answer={'question':'q1','answer':'NUR.AISYAH','evidence':'MSG-104 shows delivery to nur.aisyah'}
        r=self.post('/api/cases/mailroom/answer',answer)
        self.assertTrue(r.json['correct']); self.assertEqual(r.json['score'],40)
        self.assertEqual(self.post('/api/cases/mailroom/answer',answer).json['score'],40)
        review=self.client.get('/api/facilitator',headers={'X-Facilitator-Token':'local-test-token'}).json
        self.assertIn('MSG-104',review['findings'][0]['evidence'])
        self.assertEqual(self.app.config['SESSION_COOKIE_NAME'],'sunsoc_session')
        self.assertEqual(self.post('/api/cases/mailroom/answer',{'question':'q2','answer':'wrong','evidence':'incorrect hypothesis'}).json['correct'],False)
    def test_notes_feedback_analytics_and_export(self):
        self.register()
        self.assertEqual(self.post('/api/cases/mailroom/notes',{'notes':'Timeline draft'}).status_code,200)
        self.assertEqual(self.client.get('/api/cases/mailroom').json['notes'],'Timeline draft')
        report=self.client.get('/cases/mailroom/report')
        self.assertEqual(report.status_code,200)
        self.assertIn(b'Timeline draft',report.data)
        self.assertIn(b'MAI-005',report.data)
        self.assertNotIn(b'writeup',report.data)
        self.assertEqual(self.post('/api/feedback',{'consent':True,'pre':2,'post':4,'university':'Test only','comment':'Useful'}).status_code,201)
        analytics=self.client.get('/api/facilitator',headers={'X-Facilitator-Token':'local-test-token'}).json
        self.assertEqual(analytics['metrics']['feedback_responses'],1)
        self.assertEqual(analytics['metrics']['confidence_change'],2)
        self.assertEqual(self.client.get('/api/export').json['name'],'analyst')
    def test_login_and_account_separation(self):
        self.register(); self.post('/api/cases/mailroom/notes',{'notes':'Private note'})
        self.post('/api/logout',{}); self.csrf=self.client.get('/api/session').json['csrf']
        self.register('other')
        self.assertEqual(self.client.get('/api/cases/mailroom').json['notes'],'')
        self.post('/api/logout',{}); self.csrf=self.client.get('/api/session').json['csrf']
        self.assertEqual(self.post('/api/login',{'name':'analyst','password':'incorrect-password'}).status_code,401)
        r=self.post('/api/login',{'name':'analyst','password':'long-password-123'}); self.assertEqual(r.status_code,200); self.csrf=r.json['csrf']
        self.assertEqual(self.client.get('/api/cases/mailroom').json['notes'],'Private note')
    def test_retire_publishes_solutions(self):
        self.register()
        self.assertEqual(self.client.get('/api/library').json,[])
        r=self.client.post('/api/facilitator/retire/mailroom',json={'retired':True},headers={'X-CSRF-Token':self.csrf,'X-Facilitator-Token':'local-test-token'})
        self.assertEqual(r.status_code,200)
        self.assertEqual(len(self.client.get('/api/library').json),1)


class FullRangeTest(unittest.TestCase):
    setUp=RangeTest.setUp
    tearDown=RangeTest.tearDown
    post=RangeTest.post
    register=RangeTest.register
    def test_all_eight_case_solves_filters_and_invalid_inputs(self):
        from app import CASES
        self.register('full-range')
        for cid,c in CASES.items():
            r=self.client.get('/api/cases/'+cid); self.assertEqual(r.status_code,200)
            self.assertTrue(all('answers' not in q for q in r.json['questions']))
            for q in c['questions']:
                r=self.post(f'/api/cases/{cid}/answer',{'question':q['id'],'answer':q['answers'][0],'evidence':'Test harness synthetic evidence validation'})
                self.assertTrue(r.json['correct'])
            self.assertEqual(r.json['score'],150)
        board=self.client.get('/api/scoreboard').json
        self.assertEqual(board[0]['score'],1200); self.assertEqual(board[0]['cases_complete'],8)
        logs=self.client.get('/api/cases/lateral/logs?q=7045').json
        self.assertEqual(len(logs),1); self.assertEqual(logs[0]['host'],'FS-02')
        self.assertEqual(self.client.get('/api/cases/lateral/logs?q=absent').json,[])
        self.assertEqual(self.client.get('/api/cases/lateral/logs?start=2026-09-14T10:02:14Z&end=2026-09-14T10:02:14Z').json[0]['event'],'4624')
        self.assertEqual(self.post('/api/feedback',{'consent':True,'pre':True,'post':4}).status_code,400)
        self.assertEqual(self.post('/api/cases/mailroom/answer',{'question':'q1','answer':[],'evidence':'test evidence'}).status_code,400)
        self.assertEqual(self.client.get('/data/cases.json').status_code,404)
        # Field names are not searchable content: 'detail' should not match every row.
        self.assertEqual(self.client.get('/api/cases/lateral/logs?q=detail').json,[])

if __name__=='__main__': unittest.main()
