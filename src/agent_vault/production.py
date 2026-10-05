"""Production sidecar: existing site auth, PostgreSQL history, scoped publication."""
import hashlib, html, json, os, re, secrets, tempfile, threading, uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import psycopg2
from psycopg2.extras import Json
from .admin import ADMIN
from .core import page, render_body
from .knowledge import Knowledge
from .knowledge_mcp import rpc
ROOT=Path(os.environ.get('VAULT_SITE','/var/www/html/vault')).resolve()
DSN=os.environ.get('VAULT_DSN','dbname=agentvault user=agentvault host=/var/run/postgresql')
ORIGIN='https://qiuyiwu.com'
LOCK=threading.RLock()
TOKEN=secrets.token_urlsafe(32)
def sha(b):return hashlib.sha256(b).hexdigest()
def target(rel):
    p=(ROOT/rel).resolve()
    if ROOT not in p.parents or p.suffix!='.html' or rel.split('/')[0] not in ('books','reading','digest','html'):raise ValueError('无效发布路径')
    return p

def atomic(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    fd,n=tempfile.mkstemp(prefix='.vault-',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
        os.chmod(n,0o664);os.replace(n,p)
    finally:
        if os.path.exists(n):os.unlink(n)

def connect():return psycopg2.connect(DSN)
KNOWLEDGE=Knowledge(connect,ROOT,os.environ.get("VAULT_BUILDERS_INDEX","/var/www/html/data/ai-builders-digest/index.json"))
def init():
    with connect() as db,db.cursor() as c:
        c.execute('CREATE TABLE IF NOT EXISTS documents(id text PRIMARY KEY,path text UNIQUE NOT NULL,published integer NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS revisions(id text REFERENCES documents(id),revision integer,record jsonb NOT NULL,created timestamptz DEFAULT now(),PRIMARY KEY(id,revision)); CREATE TABLE IF NOT EXISTS publications(id bigserial PRIMARY KEY,document text,revision integer,before_bytes bytea,after_hash text,state text,created timestamptz DEFAULT now());')
    scan();KNOWLEDGE.init()
def scan():
    with LOCK,connect() as db,db.cursor() as c:
        c.execute('SELECT pg_advisory_xact_lock(5095001)')
        for p in ROOT.rglob('*.html'):
            rel=p.relative_to(ROOT).as_posix()
            if len(p.relative_to(ROOT).parts)<2 or (p.name=='index.html' and len(p.relative_to(ROOT).parts)==2):continue
            try:target(rel)
            except ValueError:continue
            ident='live-'+sha(rel.encode())[:24]
            c.execute('SELECT id,published FROM documents WHERE path=%s',(rel,));existing=c.fetchone()
            b=p.read_bytes();s=b.decode('utf-8');m=re.search(r'<title[^>]*>(.*?)</title>',s,re.S|re.I)
            title=html.unescape(re.sub('<[^>]+>','',m[1])).strip() if m else p.stem
            if existing:
                ident,published=existing
                c.execute('SELECT revision,record FROM revisions WHERE id=%s ORDER BY revision DESC LIMIT 1',(ident,));v,old=c.fetchone()
                c.execute("SELECT after_hash FROM publications WHERE document=%s AND revision=%s AND state='published' ORDER BY id DESC LIMIT 1",(ident,published));ph=c.fetchone()
                known=ph[0] if ph else old['base_hash']
                if v==published and known!=sha(b):
                    r=dict(id=ident,title=title,summary='',collection=rel.split('/')[0],kind='html',content=s,url='/vault/'+quote(rel),revision=v+1,base_hash=sha(b))
                    c.execute('INSERT INTO revisions(id,revision,record) VALUES(%s,%s,%s)',(ident,v+1,Json(r)))
                    c.execute('UPDATE documents SET published=%s WHERE id=%s',(v+1,ident))
                continue
            r=dict(id=ident,title=title,summary='',collection=rel.split('/')[0],kind='html',content=s,url='/vault/'+quote(rel),revision=0,base_hash=sha(b))
            c.execute('INSERT INTO documents VALUES(%s,%s,0)',(ident,rel));c.execute('INSERT INTO revisions(id,revision,record) VALUES(%s,0,%s)',(ident,Json(r)))
def get(ident,revision=None):
    with connect() as db,db.cursor() as c:
        c.execute('SELECT path,published FROM documents WHERE id=%s',(ident,));d=c.fetchone()
        if not d:raise ValueError('成果不存在')
        c.execute('SELECT record FROM revisions WHERE id=%s '+('ORDER BY revision DESC LIMIT 1' if revision is None else 'AND revision=%s'),(ident,) if revision is None else (ident,revision));row=c.fetchone()
        if not row:raise ValueError('版本不存在')
        r=row[0];p=target(d[0]);r['live_hash']=sha(p.read_bytes()) if p.exists() else None;r['published_revision']=d[1] if p.exists() else None
        c.execute('SELECT revision,created::text FROM revisions WHERE id=%s ORDER BY revision DESC',(ident,));r['history']=[dict(revision=v,created=t) for v,t in c.fetchall()];return r
def listing():
    scan()
    with connect() as db,db.cursor() as c:c.execute('SELECT id FROM documents ORDER BY path');ids=[x[0] for x in c.fetchall()]
    return [{k:v for k,v in get(i).items() if k not in ('content','history')} for i in ids]
def save(data):
    for k in ('title','content','summary','collection','kind'):
        if not isinstance(data.get(k),str):raise ValueError('缺少字段 '+k)
    if not data['title'].strip() or not data['content'].strip():raise ValueError('标题和正文不能为空')
    if data['collection'] not in ('books','reading','digest','html') or data['kind'] not in ('html','markdown'):raise ValueError('无效格式')
    ident=data.get('id') or 'doc-'+str(uuid.uuid4())
    with LOCK,connect() as db,db.cursor() as c:
        c.execute('SELECT pg_advisory_xact_lock(5095001)');c.execute('SELECT path,published FROM documents WHERE id=%s FOR UPDATE',(ident,));d=c.fetchone()
        c.execute('SELECT revision,record FROM revisions WHERE id=%s ORDER BY revision DESC LIMIT 1',(ident,));prev=c.fetchone();v=prev[0] if prev else 0
        if data.get('expected')!=v:raise ValueError('版本冲突，请重新打开')
        if d:
            old=prev[1];p=target(d[0]);live=sha(p.read_bytes()) if p.exists() else None
            if data.get('live_hash')!=live:raise ValueError('线上内容已变化，请重新打开并比较')
            c.execute("SELECT after_hash FROM publications WHERE document=%s AND revision=%s AND state='published' ORDER BY id DESC LIMIT 1",(ident,d[1]));ph=c.fetchone()
            known=ph[0] if ph else old['base_hash']
            if v==d[1] and known!=live:raise ValueError('外部更新尚未导入，请刷新管理页并重新打开')
            if old['collection']!=data['collection'] or old['kind']!=data['kind']:raise ValueError('不能更改已有成果格式或集合')
            if v>d[1] and old['base_hash']!=live:raise ValueError('外部智能体更新了线上正文，当前草稿已过期，请先人工合并')
            rel=d[0]
        else:
            if data.get('id'):raise ValueError('成果不存在')
            rel=data['collection']+'/'+ident+'.html';live=None;c.execute('INSERT INTO documents VALUES(%s,%s,0)',(ident,rel))
        r={k:data[k] for k in ('title','content','summary','collection','kind')};r.update(id=ident,revision=v+1,url='/vault/'+quote(rel),base_hash=live)
        c.execute('INSERT INTO revisions(id,revision,record) VALUES(%s,%s,%s)',(ident,v+1,Json(r)))
    return get(ident)
def publish(ident,revision):
    with LOCK:
        r=get(ident)
        if revision!=r['revision']:raise ValueError('只能发布当前草稿，请先将历史版本另存')
        with connect() as db,db.cursor() as c:
            c.execute('SELECT pg_advisory_xact_lock(5095001)');c.execute('SELECT path,published FROM documents WHERE id=%s FOR UPDATE',(ident,));rel,published=c.fetchone();p=target(rel)
            c.execute('SELECT max(revision) FROM revisions WHERE id=%s',(ident,))
            if c.fetchone()[0]!=revision:raise ValueError('草稿已更新')
            before=p.read_bytes() if p.exists() else None
            if published==revision and before is not None:return get(ident)
            if (sha(before) if before is not None else None)!=r['base_hash']:raise ValueError('线上文件已被外部更新，拒绝覆盖')
            body=r['content']
            if r['kind']=='html':body=re.sub(r'<title[^>]*>.*?</title>',lambda m:'<title>'+html.escape(r['title'])+'</title>',body,count=1,flags=re.S|re.I)
            out=(body if r['kind']=='html' else page(r['title'],'<a href="/vault/">返回成果库</a><h1>'+html.escape(r['title'])+'</h1>'+render_body(r['content']))).encode()
            c.execute("INSERT INTO publications(document,revision,before_bytes,after_hash,state) VALUES(%s,%s,%s,%s,'prepared') RETURNING id",(ident,revision,before,sha(out)));job=c.fetchone()[0]
        # Durable recovery record exists before filesystem mutation.
        atomic(p,out)
        with connect() as db,db.cursor() as c:
            c.execute('UPDATE documents SET published=%s WHERE id=%s',(revision,ident));c.execute("UPDATE publications SET state='published' WHERE id=%s",(job,))
    return get(ident)
def recover():
    with connect() as db,db.cursor() as c:
        c.execute("SELECT p.id,p.document,p.revision,p.after_hash,d.path FROM publications p JOIN documents d ON d.id=p.document WHERE p.state='prepared'")
        for job,ident,rev,h,rel in c.fetchall():
            p=target(rel);done=p.exists() and sha(p.read_bytes())==h
            if done:c.execute('UPDATE documents SET published=%s WHERE id=%s',(rev,ident))
            c.execute('UPDATE publications SET state=%s WHERE id=%s',('published' if done else 'interrupted',job))

def shell():
    return ADMIN.replace('<header><strong>Vault 管理</strong>','<header><strong>Vault 管理</strong><a href="/admin/vault/read">阅读笔记</a><a href="/vault/analytics.html">归档看板</a><a href="/admin/vault/insights">跨文章洞察</a><a href="/admin/vault/brief">每日简报</a>').replace('TOKEN',json.dumps(TOKEN)).replace('http://127.0.0.1:8765/','/vault/').replace("'http://127.0.0.1:8765'+x.url","x.url").replace('本机管理 · 发布仅更新本地','生产管理 · 草稿保存到数据库').replace('发布到本地阅读库','发布到网站').replace('已发布到本地阅读库','已发布到网站').replace("'/api/","'/api/inside/vault/").replace('expected:selected?.revision||0','expected:selected?.revision||0,live_hash:selected?.live_hash??null').replace("if(x.id?.startsWith('legacy-'))$('history').add(new Option('原始快照 v0','0'));",'')
def public_catalog():
    result=[]
    for p in ROOT.rglob('*.html'):
        rel=p.relative_to(ROOT).as_posix()
        if len(p.relative_to(ROOT).parts)<2 or (p.name=='index.html' and len(p.relative_to(ROOT).parts)==2):continue
        try:target(rel)
        except ValueError:continue
        t=p.read_text();m=re.search(r'<title[^>]*>(.*?)</title>',t,re.S|re.I)
        result.append(dict(title=html.unescape(re.sub('<[^>]+>','',m[1])).strip() if m else p.stem,collection=rel.split('/')[0],url='/vault/'+quote(rel),reader_url='/admin/vault/read?url='+quote('/vault/'+rel,safe=''),modified=p.stat().st_mtime))
    return sorted(result,key=lambda r:r['modified'],reverse=True)
LIBRARY="""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Vault · 成果库</title><style>body{background:#faf8f3;color:#292623;font:16px/1.7 system-ui;max-width:1080px;margin:40px auto;padding:0 24px}nav{display:flex;gap:18px;flex-wrap:wrap}a{color:#854530}h1{font-size:42px;margin-bottom:8px}input,select{font:inherit;padding:10px;border:1px solid #ddd;border-radius:8px;background:white}input{width:min(55%,540px)}#list{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-top:24px}article{border:1px solid #ddd;border-radius:10px;background:white;padding:20px}small{display:block;color:#777}article a{font-size:18px;text-decoration:none}</style><nav><a href="/">邱懿武</a><a href="/admin/vault/">管理成果</a><a href="/admin/vault/read">阅读笔记</a><a href="/vault/analytics.html">归档看板</a><a href="/admin/vault/insights">跨文章洞察</a><a href="/admin/vault/brief">每日简报</a></nav><h1>Vault · 成果库</h1><p>阅读、榨书、日报与 HTML 作品，持续整理，随时回看。</p><input id="q" placeholder="搜索标题…" aria-label="搜索标题"><select id="collection" aria-label="集合"><option value="">全部集合</option><option value="books">榨书档案</option><option value="reading">阅读档案</option><option value="digest">日报</option><option value="html">HTML 成果</option></select><p id="count">加载中…</p><div id="list"></div><script>let rows=[];const q=document.querySelector('#q'),c=document.querySelector('#collection');function draw(){let found=rows.filter(x=>(!c.value||x.collection===c.value)&&x.title.toLowerCase().includes(q.value.toLowerCase()));document.querySelector('#count').textContent=found.length+' 份成果';const list=document.querySelector('#list');list.replaceChildren();for(const x of found){let a=document.createElement('a');a.href=x.url;a.textContent=x.title;let s=document.createElement('small');s.textContent=x.collection;let card=document.createElement('article');card.append(s,a);const r=document.createElement('a');r.href=x.reader_url;r.textContent='划线 · 笔记';r.style.cssText='display:block;font-size:13px;margin-top:12px';card.append(r);list.append(card)}}q.oninput=c.onchange=draw;fetch('/vault/catalog.json').then(r=>{if(!r.ok)throw Error();return r.json()}).then(x=>{rows=x;draw()}).catch(()=>document.querySelector('#count').textContent='暂时无法加载，请稍后刷新');</script></html>"""
class Handler(BaseHTTPRequestHandler):
    def reply(self,status,obj,ctype='application/json; charset=utf-8'):
        b=(obj if isinstance(obj,str) else json.dumps(obj,ensure_ascii=False)).encode();self.send_response(status)
        for k,v in {'Content-Type':ctype,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Content-Length':str(len(b))}.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(b)
    def authenticated(self):
        try:
            req=Request('http://127.0.0.1:5050/api/inside/verify',headers={'Cookie':self.headers.get('Cookie',''),'Authorization':self.headers.get('Authorization','')})
            with urlopen(req,timeout=5) as r:return r.status==200
        except Exception:return False
    def agent_allowed(self):
        if self.headers.get('Origin') not in (None,ORIGIN):return False
        try:token=Path(os.environ.get('VAULT_AGENT_TOKEN_FILE','/var/lib/agent-vault/read-token')).read_text().strip()
        except OSError:return False
        return bool(token) and secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+token)
    def do_GET(self):
        if urlsplit(self.path).path=='/api/vault-mcp':
            if not self.agent_allowed():return self.reply(401,{'error':'read-only credential required'})
            return self.reply(405,{'error':'SSE stream not offered; use POST'})
        if self.path=='/vault/reader-link.js':return self.reply(200,(Path(__file__).parent/'web/reader-link.js').read_text(),'application/javascript; charset=utf-8')
        if self.path=='/vault/':return self.reply(200,LIBRARY,'text/html; charset=utf-8')
        if self.path=='/vault/catalog.json':return self.reply(200,public_catalog())
        if not self.authenticated():return self.reply(401,{'error':'请先登录后台'})
        try:
            u=urlsplit(self.path);q=parse_qs(u.query)
            if u.path in ('/admin/vault/read','/admin/vault/insights','/admin/vault/brief'):
                content=(Path(__file__).parent/'web/knowledge.html').read_text().replace('__VAULT_CSRF__',json.dumps(TOKEN))
                return self.reply(200,content,'text/html; charset=utf-8')
            if u.path=='/admin/vault/':return self.reply(200,shell(),'text/html; charset=utf-8')
            if u.path.startswith('/api/inside/vault/knowledge/'):
                action=u.path.rsplit('/',1)[-1];arg=lambda key,default='':q.get(key,[default])[0]
                if action=='search':return self.reply(200,KNOWLEDGE.search(arg('q'),250))
                if action=='read':return self.reply(200,KNOWLEDGE.document(arg('id')) if arg('id') else KNOWLEDGE.document_url(arg('url')))
                if action=='notes':return self.reply(200,KNOWLEDGE.notes(arg('doc_id') or None))
                if action=='related':return self.reply(200,KNOWLEDGE.related(arg('id')))
                if action=='analytics':return self.reply(200,KNOWLEDGE.analytics(arg('start'),arg('end'),arg('collection')))
                if action=='brief':return self.reply(200,KNOWLEDGE.brief(arg('day') or None))
                if action=='mcp-config':
                    key=Path(os.environ.get('VAULT_AGENT_TOKEN_FILE','/var/lib/agent-vault/read-token')).read_text().strip()
                    return self.reply(200,{'mcpServers':{'vault':{'url':ORIGIN+'/api/vault-mcp','headers':{'Authorization':'Bearer '+key}}},'_notice':'Read-only corpus credential. Excludes private notes and unpublished drafts. Client configuration syntax may vary.'})
                return self.reply(404,{'error':'unknown knowledge endpoint'})
            if u.path.endswith('/documents'):return self.reply(200,listing())
            if u.path.endswith('/document'):return self.reply(200,get(q['id'][0],int(q['revision'][0]) if 'revision' in q else None))
            self.reply(404,{'error':'not found'})
        except (ValueError,KeyError) as e:self.reply(400,{'error':str(e)})
    def do_POST(self):
        if urlsplit(self.path).path=='/api/vault-mcp':
            if not self.agent_allowed():return self.reply(401,{'error':'read-only credential required'})
            if self.headers.get('MCP-Protocol-Version','2025-03-26') not in ('2025-03-26','2025-06-18'):return self.reply(400,{'error':'unsupported protocol version'})
            try:
                n=int(self.headers.get('Content-Length',0))
                if not 0<n<=100000:raise ValueError('invalid message length')
                result=rpc(KNOWLEDGE,json.loads(self.rfile.read(n)))
                return self.reply(202 if result is None else 200,'' if result is None else result)
            except (ValueError,TypeError) as e:return self.reply(400,{'error':str(e)})
        if not self.authenticated():return self.reply(401,{'error':'请先登录后台'})
        if self.headers.get('Origin')!=ORIGIN or not secrets.compare_digest(self.headers.get('X-Vault-Token',''),TOKEN):return self.reply(403,{'error':'请刷新管理页后重试'})
        try:
            n=int(self.headers.get('Content-Length',0))
            if not 0<n<=5_000_000:raise ValueError('请求大小无效')
            d=json.loads(self.rfile.read(n))
            if self.path=='/api/inside/vault/knowledge/note-save':return self.reply(200,KNOWLEDGE.note_save(d))
            if self.path=='/api/inside/vault/knowledge/entity-save':return self.reply(200,KNOWLEDGE.entity_save(d))
            if self.path=='/api/inside/vault/knowledge/pack':return self.reply(200,KNOWLEDGE.pack(d['ids'],d.get('include_notes') is True))
            if self.path.endswith('/save'):return self.reply(200,save(d))
            if self.path.endswith('/publish'):return self.reply(200,publish(d['id'],int(d['revision'])))
            self.reply(404,{'error':'not found'})
        except (ValueError,KeyError) as e:self.reply(409,{'error':str(e)})
def main():
    init();recover();ThreadingHTTPServer(('127.0.0.1',5095),Handler).serve_forever()
if __name__=='__main__':main()
