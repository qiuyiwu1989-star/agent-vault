"""Owner-only source reading; independently scoped append-only Agent ingestion."""
import os,json,re,sqlite3,hashlib,secrets
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,parse_qs
BASE=Path(os.environ.get('VAULT_SEMINAR_SOURCES','/var/lib/agent-vault/seminar-sources'))
DOC=re.compile(r'doc-[A-Za-z0-9_-]{1,100}\Z')
TOOL={'name':'vault_append_seminar_dialogue','description':'Append user-authorized original visible dialogue to a private seminar archive. Stable source_id and message id deduplicate retries. Cannot read private archives or change public articles. Exclude hidden reasoning, system instructions and tool logs.','inputSchema':{'type':'object','properties':{'document_id':{'type':'string'},'source_id':{'type':'string'},'messages':{'type':'array','minItems':1,'maxItems':200,'items':{'type':'object','properties':{'id':{'type':'string'},'role':{'type':'string','enum':['user','assistant']},'text':{'type':'string'},'timestamp':{'type':'string'}},'required':['id','role','text'],'additionalProperties':False}}},'required':['document_id','source_id','messages'],'additionalProperties':False},'annotations':{'readOnlyHint':False,'destructiveHint':False,'idempotentHint':True}}
def valid_doc(doc):
 if not isinstance(doc,str) or not DOC.fullmatch(doc):raise ValueError('无效研讨编号')
 return doc

def db():
 BASE.mkdir(parents=True,exist_ok=True,mode=0o700)
 c=sqlite3.connect(BASE/'dialogues.sqlite',timeout=15);c.row_factory=sqlite3.Row
 c.execute('CREATE TABLE IF NOT EXISTS messages (seq INTEGER PRIMARY KEY,document_id TEXT NOT NULL,source_id TEXT NOT NULL,message_id TEXT NOT NULL,role TEXT NOT NULL,text TEXT NOT NULL,timestamp TEXT NOT NULL,stored_at TEXT NOT NULL,hash TEXT NOT NULL,UNIQUE(document_id,source_id,message_id))')
 os.chmod(BASE/'dialogues.sqlite',0o600)
 return c

def append(args):
 if not isinstance(args,dict) or set(args)!={'document_id','source_id','messages'}:raise ValueError('无效追加参数')
 doc=valid_doc(args['document_id']);source=args['source_id'];messages=args['messages']
 if not isinstance(source,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}',source):raise ValueError('无效来源编号')
 if not isinstance(messages,list) or not 1<=len(messages)<=200:raise ValueError('每批需要 1–200 条消息')
 rows=[]
 for m in messages:
  if not isinstance(m,dict) or set(m)-{'id','role','text','timestamp'}:raise ValueError('无效消息字段')
  ident=m.get('id');role=m.get('role');text=m.get('text');stamp=m.get('timestamp','')
  if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}',ident) or role not in ('user','assistant'):raise ValueError('无效消息编号或角色')
  if not isinstance(text,str) or not text.strip() or len(text)>100000:raise ValueError('消息正文需为 1–100000 字符')
  if not isinstance(stamp,str) or len(stamp)>50:raise ValueError('无效时间')
  if stamp:
   try:datetime.fromisoformat(stamp.replace('Z','+00:00'))
   except ValueError:raise ValueError('请使用 ISO 时间或留空')
  digest=hashlib.sha256(json.dumps([role,text,stamp],ensure_ascii=False).encode()).hexdigest();rows.append((ident,role,text,stamp,digest))
 c=db();added=0
 try:
  with c:
   c.execute('BEGIN IMMEDIATE')
   for ident,role,text,stamp,digest in rows:
    old=c.execute('SELECT hash FROM messages WHERE document_id=? AND source_id=? AND message_id=?',(doc,source,ident)).fetchone()
    if old:
     if old['hash']!=digest:raise ValueError('同一消息编号的内容不同；原文不会被覆盖，请用新编号追加更正')
     continue
    c.execute('INSERT INTO messages(document_id,source_id,message_id,role,text,timestamp,stored_at,hash) VALUES(?,?,?,?,?,?,?,?)',(doc,source,ident,role,text,stamp,datetime.now(timezone.utc).isoformat(),digest));added+=1
  return {'document_id':doc,'added':added,'duplicates':len(rows)-added,'private':True}
 finally:c.close()

def read(doc,after=0):
 valid_doc(doc);c=db()
 try:
  rows=[dict(r) for r in c.execute('SELECT seq,source_id,message_id,role,text,timestamp,stored_at FROM messages WHERE document_id=? AND seq>? ORDER BY seq LIMIT 101',(doc,after))]
  total=c.execute('SELECT count(*) FROM messages WHERE document_id=?',(doc,)).fetchone()[0]
  return {'messages':rows[:100],'total':total,'next_after':rows[99]['seq'] if len(rows)>100 else None}
 finally:c.close()

def owner(h):
 expected=os.environ.get('VAULT_SEMINAR_OWNER','')
 return bool(expected) and h.annotation_owner()==expected

def agent(h):
 if h.headers.get('Origin') not in (None,'https://qiuyiwu.com'):return False
 try:key=(BASE/'append-token').read_text().strip()
 except OSError:return False
 return bool(key) and secrets.compare_digest(h.headers.get('Authorization',''),'Bearer '+key)

def handle(h,method,csrf,lookup):
 u=urlsplit(h.path);prefix='/api/inside/vault/seminar-sources/';page=u.path=='/admin/vault/seminar-sources'
 if not page and not u.path.startswith(prefix):return False
 if not owner(h):h.reply(403,{'error':'仅本人登录后可查看原始资料'});return True
 try:
  q=parse_qs(u.query);doc=valid_doc(q.get('id',[''])[0]);record=lookup(doc)
  if record.get('collection')!='seminar':raise ValueError('该文档不是研讨')
  if page and method=='GET':
   body=(Path(__file__).parent/'web/seminar-sources.html').read_text().replace('__CONFIG__',json.dumps({'id':doc,'csrf':csrf,'title':record.get('title','研讨')},ensure_ascii=False).replace('<','\\u003c'))
   h.reply(200,body,'text/html; charset=utf-8');return True
  action=u.path[len(prefix):]
  if method=='GET' and action=='status':h.reply(200,{'total':read(doc)['total']});return True
  if method=='GET' and action=='messages':h.reply(200,read(doc,max(0,int(q.get('after',['0'])[0]))));return True
  if method=='GET' and action=='transcript':
   matches=sorted((BASE/doc).glob('*/邱懿武的视频会议 1012.txt'))
   if not matches:raise ValueError('本篇未附会议转写')
   h.reply(200,matches[0].read_text(),'text/plain; charset=utf-8');return True
  if method=='GET' and action=='agent-config':
   key=(BASE/'append-token').read_text().strip();h.reply(200,{'mcpServers':{'seminar-dialogue-append':{'url':'https://qiuyiwu.com/api/vault-mcp','headers':{'Authorization':'Bearer '+key}}},'document_id':doc,'scope':'append-only; no private reading'});return True
  if method=='POST' and action=='append':
   if h.headers.get('Origin')!='https://qiuyiwu.com' or not secrets.compare_digest(h.headers.get('X-Vault-Token',''),csrf):h.reply(403,{'error':'请刷新页面后重试'});return True
   n=int(h.headers.get('Content-Length','0'))
   if not 0<n<=1000000:raise ValueError('每批最多 1 MB')
   args=json.loads(h.rfile.read(n))
   if args.get('document_id')!=doc:raise ValueError('研讨编号不一致')
   h.reply(200,append(args));return True
  h.reply(404,{'error':'not found'})
 except (ValueError,KeyError,TypeError) as e:h.reply(400,{'error':str(e)})
 return True

FOOTER='''<section id="seminar-source-entry" hidden style="max-width:900px;margin:32px auto;padding:24px;border-top:1px solid #ddd"><h2>研讨原始资料</h2><p>保留当时的提问、回答与后续补充，仅本人登录可查看。</p><a id="seminar-source-link">查看原始对话与追加记录 →</a></section><script>(async()=>{const doc=location.pathname.split('/').pop().replace(/\\.html$/,'');if(!/^doc-[A-Za-z0-9_-]+$/.test(doc))return;try{const r=await fetch('/api/inside/vault/seminar-sources/status?id='+encodeURIComponent(doc),{credentials:'same-origin'});if(!r.ok)return;const a=document.getElementById('seminar-source-link');a.href='/admin/vault/seminar-sources?id='+encodeURIComponent(doc);document.getElementById('seminar-source-entry').hidden=false}catch(e){}})();</script>'''
def decorate(content,path):
 if re.fullmatch(r'/vault/seminar/doc-[A-Za-z0-9_-]+\.html',path) and 'id="seminar-source-entry"' not in content:return content.replace('</body>',FOOTER+'</body>')
 return content
