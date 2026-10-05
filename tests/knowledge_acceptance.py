"""PostgreSQL + real HTTP acceptance in an isolated schema and temporary corpus."""
import json,tempfile,uuid,threading,re
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from agent_vault import production as p
from agent_vault.knowledge import Knowledge
original=p.DSN;schema='knowledge_test_'+uuid.uuid4().hex
with p.connect() as db,db.cursor() as c:c.execute('CREATE SCHEMA '+schema)
try:
 with tempfile.TemporaryDirectory() as tmp:
  p.ROOT=Path(tmp);p.DSN=original+' options=-csearch_path='+schema;p.KNOWLEDGE=Knowledge(p.connect,p.ROOT,p.ROOT/'builders.json')
  (p.ROOT/'reading').mkdir();f=p.ROOT/'reading/2026-10-05-note.html';f.write_text('<title>Reading</title><p>作者：叶军</p><p>重点😀正文。Agent 工作流值得讨论。</p>')
  p.init();doc=p.KNOWLEDGE.corpus()[0];a=doc['text'].index('重点');b=a+len('重点😀正文')
  class TestHandler(p.Handler):
   def authenticated(self):return self.headers.get('X-Test-Auth')=='yes'
   def agent_allowed(self):return self.headers.get('Authorization')=='Bearer test-read-only'
   def log_message(self,*args):pass
  server=ThreadingHTTPServer(('127.0.0.1',0),TestHandler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_port)
  def req(path,data=None,auth=True,origin=p.ORIGIN,token=p.TOKEN,extra=None):
   headers={'Content-Type':'application/json','Origin':origin,'X-Vault-Token':token}
   if auth:headers['X-Test-Auth']='yes'
   if extra:headers.update(extra)
   with urlopen(Request(base+path,headers=headers,data=json.dumps(data).encode() if data is not None else None)) as r:return r.status,r.read()
  try:
   for route in ['read','insights','brief']:
    status,body=req('/admin/vault/'+route);assert status==200 and b'__VAULT_CSRF__' not in body
   data=dict(doc_id=doc['id'],start=a,end=b,quote=doc['text'][a:b],content_hash=doc['hash'],comment='需要继续讨论')
   _,body=req('/api/inside/vault/knowledge/note-save',data);note=json.loads(body);assert note['anchor']['status']=='exact'
   notes=json.loads(req('/api/inside/vault/knowledge/notes?doc_id='+doc['id'])[1]);assert notes[0]['quote']=='重点😀正文'
   _,body=req('/api/inside/vault/knowledge/note-save',dict(id=note['id'],doc_id=doc['id'],expected=1,comment='修订评论'));assert json.loads(body)['version']==2
   for kwargs,expected in [({'auth':False},401),({'origin':'https://evil.invalid'},403),({'token':'wrong'},403)]:
    try:req('/api/inside/vault/knowledge/note-save',data,**kwargs);raise AssertionError('security gate missed')
    except HTTPError as e:assert e.code==expected
   f.write_text('<title>Reading</title><p>新增前言</p><p>作者：叶军</p><p>重点😀正文。Agent 工作流值得讨论。</p>')
   notes=p.KNOWLEDGE.notes(doc['id']);assert notes[0]['anchor']['status']=='relocated'
   try:p.KNOWLEDGE.note_save(data);raise AssertionError('stale anchor accepted')
   except ValueError:pass
   brief=p.KNOWLEDGE.brief('2026-10-05');assert brief['today_count']==1;assert brief['items'][0]['id']==doc['id']
   analytics=p.KNOWLEDGE.analytics();assert analytics['notes']==1;assert any(e['name']=='叶军' for e in analytics['entities'])
   p.KNOWLEDGE.entity_save(dict(kind='person',name='叶军',aliases=['叶老师']));assert any(e['confirmed'] for e in p.KNOWLEDGE.entities() if e['name']=='叶军')
   msg=dict(jsonrpc='2.0',id=1,method='initialize',params={'protocolVersion':'2025-06-18'})
   _,raw=req('/api/vault-mcp',msg,auth=False,extra={'Authorization':'Bearer test-read-only'});assert json.loads(raw)['result']['serverInfo']['name']=='agent-vault-readonly'
   msg.update(method='tools/call',params={'name':'vault_read','arguments':{'id':doc['id']}})
   _,raw=req('/api/vault-mcp',msg,auth=False,extra={'Authorization':'Bearer test-read-only'});assert '修订评论' not in raw.decode();assert 'private_notes' not in raw.decode()
   assert 'private_notes' not in p.KNOWLEDGE.pack([doc['id']]);assert p.KNOWLEDGE.pack([doc['id']],True)['private_notes']
   print('PASS: reader/BI/brief HTML, Unicode annotation persistence/edit, unauthenticated/CSRF denial, stale anchor protection, reanchor, analytics, entity aliases, brief storage, MCP initialize/read and private-note exclusion')
  finally:server.shutdown();server.server_close()
finally:
 p.DSN=original
 with p.connect() as db,db.cursor() as c:c.execute('DROP SCHEMA '+schema+' CASCADE')
