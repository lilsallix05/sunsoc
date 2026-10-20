import json, tempfile, threading, unittest
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from integrations.export import build
from integrations.ctfd_import import send, validate_url
from integrations.siem import ingest

class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); build(self.root)
        self.requests=[]; self.bad=False; outer=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a): pass
            def do_GET(self): self.reply({'success':True,'data':[]})
            def do_POST(self):
                raw=self.rfile.read(int(self.headers['Content-Length'])); outer.requests.append((self.path,dict(self.headers),raw))
                if self.path=='/_bulk': self.reply({'errors':outer.bad,'items':[]})
                elif self.path.endswith('/event'): self.reply({'code':1 if outer.bad else 0})
                else: self.reply({'success':True,'data':{'id':len(outer.requests)}})
            def reply(self,data):
                raw=json.dumps(data).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler); self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start(); self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self): self.server.shutdown(); self.server.server_close(); self.thread.join(); self.tmp.cleanup()
    def test_package_and_ctfd_import_resume(self):
        manifest=json.loads((self.root/'manifest.json').read_text()); self.assertEqual(len(manifest['challenges']),24)
        result=send(self.root,self.url,'test-only',self.root/'receipt.json'); self.assertEqual(result['imported'],24)
        count=len(self.requests); self.assertEqual(count,120)
        self.assertTrue(all(h['Authorization']=='Token test-only' for _,h,_ in self.requests))
        self.assertTrue(any(b'timestamp' in raw for path,_,raw in self.requests if path=='/api/v1/files'))
        send(self.root,self.url,'test-only',self.root/'receipt.json'); self.assertEqual(len(self.requests),count)
    def test_siem_acknowledgement_and_error(self):
        for kind,name,auth in [('elastic','elastic-bulk.ndjson','ApiKey test-only'),('splunk','splunk-hec.ndjson','Splunk test-only')]:
            result=ingest(kind,self.url,'test-only',self.root/name); self.assertTrue(result['accepted_by_endpoint']); self.assertFalse(result['searchability_verified']); self.assertEqual(self.requests[-1][1]['Authorization'],auth)
            self.bad=True
            with self.assertRaises(RuntimeError): ingest(kind,self.url,'test-only',self.root/name)
            self.bad=False
    def test_transport_restrictions(self):
        for url in ['http://example.com','https://user:pass@example.com','file:///tmp/test','https://example.com?token=x']:
            with self.assertRaises(ValueError): validate_url(url)
