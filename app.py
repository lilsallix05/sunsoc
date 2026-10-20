"""SunSOC: a local, synthetic investigation range. No target execution."""
import csv, io, json, os, re, secrets, sqlite3, time
from contextlib import closing
from datetime import datetime, timezone, timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, jsonify, request, session, g, render_template, Response, abort
from werkzeug.security import generate_password_hash, check_password_hash

ROOT=Path(__file__).resolve().parent
CASES={c['id']:c for c in json.loads((ROOT/'data/cases.json').read_text())}
SCHEMA='''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT UNIQUE COLLATE NOCASE,password TEXT,created REAL);
CREATE TABLE IF NOT EXISTS progress(user_id INTEGER,case_id TEXT,started REAL,notes TEXT DEFAULT '',PRIMARY KEY(user_id,case_id));
CREATE TABLE IF NOT EXISTS solves(user_id INTEGER,case_id TEXT,question TEXT,at REAL,evidence TEXT,PRIMARY KEY(user_id,case_id,question));
CREATE TABLE IF NOT EXISTS attempts(user_id INTEGER,case_id TEXT,question TEXT,at REAL,correct INTEGER);
CREATE TABLE IF NOT EXISTS hints(user_id INTEGER,case_id TEXT,number INTEGER,PRIMARY KEY(user_id,case_id,number));
CREATE TABLE IF NOT EXISTS feedback(user_id INTEGER PRIMARY KEY,pre INTEGER,post INTEGER,university TEXT,comment TEXT,at REAL);
CREATE TABLE IF NOT EXISTS retired(case_id TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS auth_attempts(ip TEXT,at REAL);
'''

def create_app(config=None):
    app=Flask(__name__)
    instance=ROOT/'instance'; instance.mkdir(exist_ok=True,mode=0o700)
    secret=instance/'session.key'
    if not secret.exists():
        try:
            with secret.open('x') as f: f.write(secrets.token_hex(32))
            secret.chmod(0o600)
        except FileExistsError: pass
    app.config.update(SECRET_KEY=os.getenv('SUNSOC_SECRET',secret.read_text().strip()),DATABASE=str(instance/'sunsoc.db'),FACILITATOR_TOKEN=os.getenv('SUNSOC_FACILITATOR_TOKEN',''),MAX_CONTENT_LENGTH=64*1024,SESSION_COOKIE_NAME='sunsoc_session',SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('SUNSOC_HTTPS')=='1',PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
    if config: app.config.update(config)
    with closing(sqlite3.connect(app.config['DATABASE'])) as db:
        db.executescript(SCHEMA); db.commit()

    def db():
        if 'db' not in g:
            g.db=sqlite3.connect(app.config['DATABASE'],timeout=10); g.db.row_factory=sqlite3.Row
        return g.db
    @app.teardown_appcontext
    def close(_):
        if 'db' in g: g.db.close()
    def token():
        if 'csrf' not in session: session['csrf']=secrets.token_hex(24)
        return session['csrf']
    def user():
        return db().execute('SELECT id,name FROM users WHERE id=?',(session.get('uid'),)).fetchone()
    def login(fn):
        @wraps(fn)
        def wrapped(*a,**kw):
            if not user(): abort(401,description='Sign in to begin an investigation.')
            return fn(*a,**kw)
        return wrapped
    def facilitator():
        expected=app.config['FACILITATOR_TOKEN']
        if not expected or not secrets.compare_digest(request.headers.get('X-Facilitator-Token',''),expected): abort(403,description='A facilitator token is required.')
    def case_or_404(cid):
        if cid not in CASES: abort(404,description='Case not found.')
        return CASES[cid]
    def body():
        data=request.get_json(silent=True)
        if not isinstance(data,dict): abort(400,description='Send a JSON object.')
        return data
    def string(data,key,maximum=5000):
        val=data.get(key,'')
        if not isinstance(val,str) or len(val)>maximum: abort(400,description=f'Invalid {key}.')
        return val.strip()
    @app.before_request
    def csrf():
        if request.method in ('POST','PUT','PATCH','DELETE'):
            if not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),session.get('csrf','missing')): abort(403,description='Session check failed. Refresh and retry.')
    @app.after_request
    def headers(resp):
        resp.headers['Content-Security-Policy']="default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        resp.headers['X-Content-Type-Options']='nosniff'; resp.headers['X-Frame-Options']='DENY'; resp.headers['Referrer-Policy']='same-origin'
        if request.path.startswith('/api/'): resp.headers['Cache-Control']='no-store'
        return resp
    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def err(e): return jsonify(error=e.description),e.code
    def state(uid,cid):
        c=CASES[cid]
        solved=[r['question'] for r in db().execute('SELECT question FROM solves WHERE user_id=? AND case_id=?',(uid,cid))]
        count=db().execute('SELECT count(*) FROM hints WHERE user_id=? AND case_id=?',(uid,cid)).fetchone()[0]
        p=db().execute('SELECT * FROM progress WHERE user_id=? AND case_id=?',(uid,cid)).fetchone()
        return {'solved':solved,'hint_count':count,'score':max(0,len(solved)*50-count*10),'notes':p['notes'] if p else '', 'started':p['started'] if p else None}
    def touch(uid,cid):
        db().execute('INSERT OR IGNORE INTO progress(user_id,case_id,started) VALUES(?,?,?)',(uid,cid,time.time())); db().commit()
    def public(c):
        return {k:c[k] for k in ('id','title','level','source','minutes','brief','provenance')}
    @app.get('/')
    def index(): return render_template('index.html')
    @app.get('/api/session')
    def get_session():
        u=user(); return jsonify(user=dict(u) if u else None,csrf=token())
    def auth_limit():
        ip=request.remote_addr; now=time.time()
        db().execute('DELETE FROM auth_attempts WHERE at<?',(now-300,))
        n=db().execute('SELECT count(*) FROM auth_attempts WHERE ip=?',(ip,)).fetchone()[0]
        if n>=20: abort(429,description='Too many sign-in attempts. Wait five minutes.')
        db().execute('INSERT INTO auth_attempts VALUES(?,?)',(ip,now)); db().commit()
    def establish(uid,name):
        session.clear(); session['uid']=uid; session.permanent=True
        return jsonify(user={'id':uid,'name':name},csrf=token())
    @app.post('/api/register')
    def register():
        auth_limit(); d=body(); name=string(d,'name',32); password=string(d,'password',128)
        if not re.fullmatch(r'[A-Za-z0-9_.-]{3,32}',name): abort(400,description='Use 3–32 letters, numbers, dots, underscores or hyphens.')
        if len(password)<12: abort(400,description='Use a password of at least 12 characters.')
        try:
            cur=db().execute('INSERT INTO users(name,password,created) VALUES(?,?,?)',(name,generate_password_hash(password),time.time())); db().commit()
        except sqlite3.IntegrityError: abort(409,description='That analyst name is already in use.')
        return establish(cur.lastrowid,name),201
    @app.post('/api/login')
    def sign_in():
        auth_limit(); d=body(); name=string(d,'name',32); password=string(d,'password',128)
        u=db().execute('SELECT * FROM users WHERE name=?',(name,)).fetchone()
        if not u or not check_password_hash(u['password'],password): abort(401,description='Name or password was not recognised.')
        return establish(u['id'],u['name'])
    @app.post('/api/logout')
    def logout(): session.clear(); return jsonify(ok=True,csrf=token())
    @app.get('/api/cases')
    @login
    def cases():
        retired={r[0] for r in db().execute('SELECT case_id FROM retired')}
        return jsonify([{**public(c),**state(session['uid'],c['id']),'retired':c['id'] in retired,'events':len(c['logs']),'questions_count':len(c['questions'])} for c in CASES.values()])
    @app.get('/api/cases/<cid>')
    @login
    def case(cid):
        c=case_or_404(cid); touch(session['uid'],cid); s=state(session['uid'],cid)
        return jsonify(**public(c),**s,questions=[{k:q[k] for k in ('id','prompt','points')} for q in c['questions']],hints=c['hints'][:s['hint_count']])
    @app.get('/api/cases/<cid>/logs')
    @login
    def logs(cid):
        rows=case_or_404(cid)['logs']; query=request.args.get('q','').casefold(); host=request.args.get('host',''); start=request.args.get('start',''); end=request.args.get('end','')
        rows=[r for r in rows if query in ' '.join(map(str,r.values())).casefold() and (not host or r['host']==host) and (not start or r['timestamp']>=start) and (not end or r['timestamp']<=end)]
        return jsonify(rows)
    @app.get('/api/cases/<cid>/evidence.csv')
    @login
    def download(cid):
        rows=case_or_404(cid)['logs']; out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
        return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename="sunsoc-{cid}.csv"'})
    @app.get('/cases/<cid>/report')
    @login
    def report(cid):
        c=case_or_404(cid); uid=session['uid']
        findings=[dict(r) for r in db().execute('SELECT question,at,evidence FROM solves WHERE user_id=? AND case_id=? ORDER BY question',(uid,cid))]
        return render_template('report.html',case=c,progress=state(uid,cid),findings=findings,analyst=user()['name'])
    @app.post('/api/cases/<cid>/notes')
    @login
    def notes(cid):
        case_or_404(cid); value=string(body(),'notes',12000); touch(session['uid'],cid)
        db().execute('UPDATE progress SET notes=? WHERE user_id=? AND case_id=?',(value,session['uid'],cid)); db().commit(); return jsonify(saved=True)
    @app.post('/api/cases/<cid>/answer')
    @login
    def answer(cid):
        c=case_or_404(cid); d=body(); q=next((q for q in c['questions'] if q['id']==d.get('question')),None)
        if not q: abort(400,description='Question not found.')
        val=string(d,'answer',200); evidence=string(d,'evidence',2000)
        if not val or len(evidence)<8: abort(400,description='Provide an answer and an evidence note of at least 8 characters.')
        touch(session['uid'],cid)
        correct=val.casefold() in [x.casefold() for x in q['answers']]
        db().execute('INSERT INTO attempts VALUES(?,?,?,?,?)',(session['uid'],cid,q['id'],time.time(),int(correct)))
        if correct: db().execute('INSERT OR IGNORE INTO solves VALUES(?,?,?,?,?)',(session['uid'],cid,q['id'],time.time(),evidence))
        db().commit()
        return jsonify(correct=correct,explanation=q['explanation'] if correct else None,**state(session['uid'],cid))
    @app.post('/api/cases/<cid>/hint')
    @login
    def hint(cid):
        c=case_or_404(cid); uid=session['uid']; touch(uid,cid)
        # Serialize hint purchase so parallel requests cannot charge the same hint twice.
        db().execute('BEGIN IMMEDIATE')
        n=db().execute('SELECT count(*) FROM hints WHERE user_id=? AND case_id=?',(uid,cid)).fetchone()[0]
        if n>=len(c['hints']): db().rollback(); abort(409,description='All hints are already open.')
        db().execute('INSERT INTO hints VALUES(?,?,?)',(uid,cid,n)); db().commit()
        return jsonify(hint=c['hints'][n],cost=10,**state(uid,cid))
    def scoreboard_data():
        out=[]
        for u in db().execute('SELECT id,name FROM users'):
            states=[state(u['id'],cid) for cid in CASES]
            out.append({'name':u['name'],'score':sum(s['score'] for s in states),'solved':sum(len(s['solved']) for s in states),'cases_complete':sum(len(s['solved'])==3 for s in states)})
        return sorted(out,key=lambda r:(-r['score'],-r['solved'],r['name'].casefold()))
    @app.get('/api/scoreboard')
    @login
    def scoreboard(): return jsonify(scoreboard_data())
    @app.get('/api/export')
    @login
    def export():
        uid=session['uid']; out={'schema_version':1,'name':user()['name'],'exported_at':datetime.now(timezone.utc).isoformat(),'dataset':'synthetic','cases':{cid:state(uid,cid) for cid in CASES},'solves':[dict(r) for r in db().execute('SELECT case_id,question,at,evidence FROM solves WHERE user_id=?',(uid,))]}
        return Response(json.dumps(out,indent=2),mimetype='application/json',headers={'Content-Disposition':'attachment; filename="sunsoc-session.json"'})
    @app.post('/api/feedback')
    @login
    def feedback():
        d=body()
        if d.get('consent') is not True: abort(400,description='Consent is required to store this optional feedback.')
        if type(d.get('pre'))!=int or type(d.get('post'))!=int or not 1<=d['pre']<=5 or not 1<=d['post']<=5: abort(400,description='Confidence scores must be integers from 1 to 5.')
        db().execute('INSERT OR REPLACE INTO feedback VALUES(?,?,?,?,?,?)',(session['uid'],d['pre'],d['post'],string(d,'university',120),string(d,'comment',2000),time.time())); db().commit(); return jsonify(saved=True),201
    def library_data():
        return [{**public(CASES[r[0]]),'writeup':CASES[r[0]]['writeup'],'questions':CASES[r[0]]['questions']} for r in db().execute('SELECT case_id FROM retired')]
    @app.get('/api/library')
    def library(): return jsonify(library_data())
    @app.get('/api/facilitator')
    def instructor():
        facilitator(); feedbacks=[dict(r) for r in db().execute('SELECT pre,post,university,comment,at FROM feedback')]; starts=db().execute('SELECT count(*) FROM progress').fetchone()[0]
        completed=[]
        for row in db().execute('SELECT user_id,case_id,max(at) AS finish,count(*) AS n FROM solves GROUP BY user_id,case_id HAVING n=3'):
            start=db().execute('SELECT started FROM progress WHERE user_id=? AND case_id=?',(row['user_id'],row['case_id'])).fetchone()[0]; completed.append(max(0,row['finish']-start))
        retired={r[0] for r in db().execute('SELECT case_id FROM retired')}
        return jsonify(cases=[{**c,'retired':c['id'] in retired} for c in CASES.values()],metrics={'registered_accounts':db().execute('SELECT count(*) FROM users').fetchone()[0],'case_starts':starts,'case_completions':len(completed),'completion_rate':len(completed)/starts if starts else None,'mean_solve_seconds':sum(completed)/len(completed) if completed else None,'feedback_responses':len(feedbacks),'confidence_change':sum(f['post']-f['pre'] for f in feedbacks)/len(feedbacks) if feedbacks else None,'universities':len({f['university'].casefold() for f in feedbacks if f['university']})},feedback=feedbacks,findings=[dict(r) for r in db().execute('SELECT u.name,s.case_id,s.question,s.at,s.evidence FROM solves s JOIN users u ON s.user_id=u.id ORDER BY s.at DESC')],measurement_note='Local account activity, not verified workshop attendance. Solve time is wall-clock since first case open; self-reported confidence is not a skills assessment.')
    @app.post('/api/facilitator/retire/<cid>')
    def retire(cid):
        facilitator(); case_or_404(cid); d=body()
        if type(d.get('retired'))!=bool: abort(400,description='retired must be true or false.')
        if d['retired']: db().execute('INSERT OR IGNORE INTO retired VALUES(?)',(cid,))
        else: db().execute('DELETE FROM retired WHERE case_id=?',(cid,))
        db().commit(); return jsonify(ok=True)
    return app

if __name__=='__main__':
    from waitress import serve
    serve(create_app(),host='127.0.0.1',port=int(os.getenv('PORT','4891')))
