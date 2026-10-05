import hashlib
import json
import tempfile
import unittest
import threading
import urllib.request
import urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
from agent_vault.core import Vault,VaultError
from agent_vault.admin import Manager,handler


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);v=Vault(self.root/'store')
        prefix='vault-migration-snapshot/published/vault/html/'
        content=b'<title>Original</title><p>old body</p>'
        digest=hashlib.sha256(content).hexdigest()
        r={'id':'legacy-demo','kind':'html','collection':'html','source_path':prefix+'demo.html','published_path':prefix+'demo.html','old_url':'/vault/html/demo.html','values':{'title':'Original'}}
        with v.connect() as db:
            db.executescript('CREATE TABLE legacy_documents(snapshot TEXT,id TEXT,record TEXT);CREATE TABLE legacy_files(snapshot TEXT,path TEXT,sha256 TEXT);CREATE TABLE legacy_blobs(sha256 TEXT,content BLOB);')
            db.execute('INSERT INTO legacy_documents VALUES(?,?,?)',('snap','legacy-demo',json.dumps(r)))
            db.execute('INSERT INTO legacy_files VALUES(?,?,?)',('snap',prefix+'demo.html',digest))
            db.execute('INSERT INTO legacy_blobs VALUES(?,?)',(digest,content))
        self.m=Manager(self.root/'store','snap',self.root/'site')
    def tearDown(self):self.tmp.cleanup()
    def draft(self):
        return dict(id='legacy-demo',expected=0,title='Changed',summary='new summary',content='<h1>new body</h1>',collection='html',kind='html')
    def test_draft_publish_and_restore(self):
        a=self.m.save(self.draft());self.assertEqual(a['revision'],1)
        self.assertIn('old body',(self.root/'site/vault/html/demo.html').read_text())
        self.m.publish(a['id'],1)
        self.assertIn('new body',(self.root/'site/vault/html/demo.html').read_text())
        self.m.publish(a['id'],0)
        self.assertIn('old body',(self.root/'site/vault/html/demo.html').read_text())
        self.assertEqual(self.m.get(a['id'])['revision'],1)
    def test_new_document_and_conflict(self):
        a=self.m.save(self.draft())
        with self.assertRaises(VaultError):self.m.save(self.draft())
        d=self.draft();d['id']=None;b=self.m.save(d)
        self.m.publish(b['id'],1)
        self.assertEqual(len(json.loads((self.root/'site/catalog.json').read_text())),2)
        self.assertEqual(len(self.m.get(a['id'])['history']),1)
    def test_id_path_rejected(self):
        d=self.draft();d['id']='../outside'
        with self.assertRaises(VaultError):self.m.save(d)
    def test_api_protection(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.m,'test-token',0))
        port=server.server_address[1];server.RequestHandlerClass=handler(self.m,'test-token',port)
        t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        try:
            url=f'http://127.0.0.1:{port}/api/documents'
            with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(url)
            self.assertEqual(e.exception.code,403)
            req=urllib.request.Request(url,headers={'X-Vault-Token':'test-token'})
            with urllib.request.urlopen(req) as response:self.assertEqual(len(json.load(response)),1)
            req=urllib.request.Request(url,headers={'X-Vault-Token':'test-token','Origin':'http://127.0.0.1:8765'})
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(req)
        finally:server.shutdown();server.server_close();t.join()
