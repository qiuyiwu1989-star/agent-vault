"""Local management UI; isolated from the origin serving imported HTML."""
import argparse
import hashlib
import html
import json
import secrets
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from .core import VaultError, page, render_body
from .reader import build, Text, Handler as ReaderHandler


class Manager:
    def __init__(self, root, snapshot, site):
        self.root=Path(root);self.snapshot=snapshot;self.site=Path(site);self.lock=threading.RLock()
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS managed_revisions(
              snapshot TEXT NOT NULL,id TEXT NOT NULL,revision INTEGER NOT NULL,record TEXT NOT NULL,created TEXT NOT NULL,
              PRIMARY KEY(snapshot,id,revision));
            CREATE TABLE IF NOT EXISTS managed_published(snapshot TEXT NOT NULL,id TEXT NOT NULL,revision INTEGER NOT NULL,
              PRIMARY KEY(snapshot,id));
            ''')
        self.refresh()

    def connect(self):
        db=sqlite3.connect(self.root/'vault.sqlite3',timeout=30);db.row_factory=sqlite3.Row;return db

    def baseline(self,db,doc_id):
        row=db.execute('SELECT record FROM legacy_documents WHERE snapshot=? AND id=?',(self.snapshot,doc_id)).fetchone()
        if not row:return None
        r=json.loads(row['record']);source=r['source_path']
        b=db.execute('SELECT b.content FROM legacy_files f JOIN legacy_blobs b ON f.sha256=b.sha256 WHERE f.snapshot=? AND f.path=?',
                     (self.snapshot,source)).fetchone()
        return dict(id=doc_id,title=r['values'].get('title',Path(source).name),collection=r['collection'],kind=r['kind'],
                    content=b['content'].decode('utf-8'),summary=r['values'].get('summary',''),date=r['values'].get('date',''),
                    url=r['old_url'],revision=0,status='snapshot')

    def get(self,doc_id,revision=None):
        with self.connect() as db:
            if revision==0:r=self.baseline(db,doc_id)
            else:
                row=db.execute('SELECT record FROM managed_revisions WHERE snapshot=? AND id=? '+
                  ('ORDER BY revision DESC LIMIT 1' if revision is None else 'AND revision=?'),
                  (self.snapshot,doc_id) if revision is None else (self.snapshot,doc_id,revision)).fetchone()
                r=json.loads(row['record']) if row else (self.baseline(db,doc_id) if revision is None else None)
            if not r:raise VaultError('没有找到该成果或版本')
            published=db.execute('SELECT revision FROM managed_published WHERE snapshot=? AND id=?',(self.snapshot,doc_id)).fetchone()
            r['published_revision']=published['revision'] if published else (0 if self.baseline(db,doc_id) else None)
            r['history']=[dict(row) for row in db.execute('SELECT revision,created FROM managed_revisions WHERE snapshot=? AND id=? ORDER BY revision DESC',(self.snapshot,doc_id))]
            return r

    def list(self):
        with self.connect() as db:
            ids={r['id'] for r in db.execute('SELECT id FROM legacy_documents WHERE snapshot=? UNION SELECT id FROM managed_revisions WHERE snapshot=?',(self.snapshot,self.snapshot))}
        return [{k:v for k,v in self.get(i).items() if k not in ('content','history')} for i in sorted(ids)]

    def save(self,data):
        doc_id=data.get('id') or 'doc-'+str(uuid.uuid4())
        if not isinstance(doc_id,str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',doc_id):raise VaultError('无效成果 ID')
        if not all(isinstance(data.get(k),str) for k in ('title','content','collection','kind','summary')):
            raise VaultError('缺少标题、正文、类型或摘要')
        if not data['title'].strip() or not data['content'].strip():raise VaultError('标题和正文不能为空')
        if data['collection'] not in ('books','reading','digest','html') or data['kind'] not in ('markdown','html'):
            raise VaultError('不支持的集合或格式')
        with self.lock,self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            head=db.execute('SELECT revision,record FROM managed_revisions WHERE snapshot=? AND id=? ORDER BY revision DESC LIMIT 1',(self.snapshot,doc_id)).fetchone()
            base=self.baseline(db,doc_id)
            current=json.loads(head['record']) if head else base
            revision=head['revision'] if head else 0
            if data.get('expected')!=revision:raise VaultError('版本冲突，请重新打开并比较修改')
            if current and (current['collection']!=data['collection'] or current['kind']!=data['kind']):
                raise VaultError('已有成果不能在此修改格式或集合')
            record={k:data[k] for k in ('title','content','collection','kind','summary')}
            record.update(id=doc_id,revision=revision+1,date=current['date'] if current else datetime.now().astimezone().date().isoformat(),
                          url=current['url'] if current else '/vault/'+data['collection']+'/'+doc_id+'.html',status='draft')
            db.execute('INSERT INTO managed_revisions VALUES(?,?,?,?,?)',(self.snapshot,doc_id,revision+1,json.dumps(record,ensure_ascii=False),datetime.now(timezone.utc).isoformat()))
        return self.get(doc_id)

    def publish(self,doc_id,revision):
        with self.lock:
            record=self.get(doc_id,revision)
            if revision!=0 and revision!=self.get(doc_id)['revision']:
                raise VaultError('请先将历史内容保存为新草稿，再发布；不会覆盖后续修订')
            with self.connect() as db:
                old=db.execute('SELECT revision FROM managed_published WHERE snapshot=? AND id=?',(self.snapshot,doc_id)).fetchone()
                db.execute('INSERT OR REPLACE INTO managed_published VALUES(?,?,?)',(self.snapshot,doc_id,revision))
            try:self.refresh()
            except Exception:
                with self.connect() as db:
                    if old:db.execute('INSERT OR REPLACE INTO managed_published VALUES(?,?,?)',(self.snapshot,doc_id,old['revision']))
                    else:db.execute('DELETE FROM managed_published WHERE snapshot=? AND id=?',(self.snapshot,doc_id))
                self.refresh();raise
            return self.get(doc_id)

    def refresh(self):
        # Local MVP rebuild: immutable historical input plus selected edited revisions.
        with self.lock:
            build(self.root,self.snapshot,self.site)
            catalog=json.loads((self.site/'catalog.json').read_text())
            by_url={x['url']:x for x in catalog}
            with self.connect() as db:
                published=list(db.execute('SELECT id,revision FROM managed_published WHERE snapshot=?',(self.snapshot,)))
            for pub in published:
                if pub['revision']==0:continue
                r=self.get(pub['id'],pub['revision'])
                content=r['content'] if r['kind']=='html' else page(r['title'],'<a href="/">返回成果库</a><h1>'+html.escape(r['title'])+'</h1>'+render_body(r['content']))
                p=self.site/r['url'].lstrip('/');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
                text=Text();text.feed(content)
                by_url[r['url']]={k:r[k] for k in ('title','collection','date','summary','url')}|{'search':' '.join([r['title']]+text.parts)}
            (self.site/'catalog.json').write_text(json.dumps(sorted(by_url.values(),key=lambda x:x['date'],reverse=True),ensure_ascii=False))


ADMIN='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Vault 管理</title>
<style>*{box-sizing:border-box}body{font:15px/1.6 system-ui;margin:0;background:#faf8f3;color:#292623}header{padding:18px 24px;display:flex;gap:22px;align-items:center;border-bottom:1px solid #ddd}header strong{font-size:22px}a{color:#854530}main{display:grid;grid-template-columns:320px 1fr;min-height:85vh}aside{padding:18px;border-right:1px solid #ddd;overflow:auto;max-height:88vh}section{padding:22px;max-width:1000px}input,textarea,select{font:inherit;padding:9px;border:1px solid #ccc;border-radius:7px;background:white}input,textarea{width:100%;margin-bottom:12px}textarea{font:13px/1.5 ui-monospace,monospace;height:42vh}button{font:inherit;padding:8px 13px;border:1px solid #c9bcae;border-radius:7px;background:white;cursor:pointer}.primary{background:#854530;color:white}label{display:block;font-size:13px;color:#70685f}#list button{display:block;width:100%;text-align:left;margin:7px 0}#list small{display:block;color:#777}#msg{padding:8px 0;min-height:38px}#meta{color:#777;font-size:13px}.actions{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}@media(max-width:750px){main{grid-template-columns:1fr}aside{max-height:220px;border-bottom:1px solid #ddd}section{padding:16px}}</style>
<header><strong>Vault 管理</strong><a href="http://127.0.0.1:8765/" target="_blank" rel="noopener">打开阅读库 ↗</a><span>本机管理 · 发布仅更新本地</span></header>
<main><aside><button id="new">＋ 新建成果</button><input id="search" aria-label="搜索成果" placeholder="搜索标题…"><div id="list"></div></aside><section><div id="meta">从左侧选择成果，或新建一份。</div><label>标题<input id="title"></label><div class="actions"><label>集合 <select id="collection"><option value="reading">阅读档案</option><option value="books">榨书档案</option><option value="digest">日报</option><option value="html">HTML 成果</option></select></label><label>格式 <select id="kind"><option value="markdown">Markdown</option><option value="html">HTML</option></select></label></div><label>摘要<input id="summary"></label><label>正文 / HTML 源码<textarea id="content" spellcheck="false"></textarea></label><div class="actions"><button id="save" class="primary">保存草稿</button><button id="publish">发布到本地阅读库</button><a id="preview" target="_blank" rel="noopener">查看已发布页 ↗</a></div><div id="msg" role="status"></div><label>历史版本<select id="history"><option value="">选择版本</option></select></label><button id="restore">载入历史内容为草稿</button><p>HTML 可在这里直接编辑；OpenDesign Docs 尚未接通。</p></section></main>
<script>
const token=TOKEN;let selected=null,items=[];const $=id=>document.getElementById(id);let busy=false;
async function api(path,data){const r=await fetch(path,{method:data?'POST':'GET',headers:{'X-Vault-Token':token,'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});const x=await r.json();if(!r.ok)throw Error(x.error);return x;}
function notice(s){$('msg').textContent=s}function draw(){const q=$('search').value.toLowerCase();$('list').replaceChildren();for(const x of items.filter(x=>x.title.toLowerCase().includes(q))){const b=document.createElement('button');b.textContent=x.title;const s=document.createElement('small');s.textContent=x.collection+' · 草稿 v'+x.revision+' / 已发布 '+(x.published_revision===null?'无':'v'+x.published_revision);b.append(s);b.onclick=()=>run(async()=>load(await api('/api/document?id='+encodeURIComponent(x.id))));$('list').append(b)}}
async function reload(){items=await api('/api/documents');draw()}
function load(x){selected=x;for(const k of ['title','summary','content','collection','kind'])$(k).value=x[k];$('collection').disabled=!!x.id;$('kind').disabled=!!x.id;$('meta').textContent=x.id?('版本 '+x.revision+' · '+x.id):'新建成果';$('preview').href=x.url?'http://127.0.0.1:8765'+x.url:'#';$('history').replaceChildren(new Option('选择版本',''));if(x.id?.startsWith('legacy-'))$('history').add(new Option('原始快照 v0','0'));for(const h of x.history||[])$('history').add(new Option('v'+h.revision+' · '+h.created,String(h.revision)));notice('')}
async function run(f){if(busy)return;busy=true;try{await f()}catch(e){notice(e.message)}finally{busy=false}}
$('search').oninput=draw;$('new').onclick=()=>load({id:null,revision:0,title:'',summary:'',content:'',collection:'reading',kind:'markdown',history:[]});
$('save').onclick=()=>run(async()=>{const d={id:selected?.id,expected:selected?.revision||0};for(const k of ['title','summary','content','collection','kind'])d[k]=$(k).value;load(await api('/api/save',d));await reload();notice('草稿已保存，阅读库暂不改变。')});
$('publish').onclick=()=>run(async()=>{if(!selected?.id)throw Error('请先保存草稿');for(const k of ['title','summary','content','collection','kind'])if($(k).value!==selected[k])throw Error('有未保存修改，请先保存草稿');load(await api('/api/publish',{id:selected.id,revision:selected.revision}));await reload();notice('已发布到本地阅读库，刷新阅读页即可看到。')});
$('restore').onclick=()=>run(async()=>{if(!selected?.id||$('history').value==='')throw Error('请选择历史版本');const old=await api('/api/document?id='+encodeURIComponent(selected.id)+'&revision='+$('history').value);for(const k of ['title','summary','content'])$(k).value=old[k];notice('历史内容已载入。点击保存草稿会创建新版本。')});run(reload);
</script></html>'''


def handler(manager,token,port):
    class Handler(BaseHTTPRequestHandler):
        def reply(self,status,obj,content_type='application/json; charset=utf-8'):
            b=obj.encode() if isinstance(obj,str) else json.dumps(obj,ensure_ascii=False).encode()
            self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
        def allowed(self,write=False):
            if self.headers.get('Host')!=f'127.0.0.1:{port}':return False
            if self.headers.get('X-Vault-Token')!=token:return False
            origin=self.headers.get('Origin')
            return not origin or origin==f'http://127.0.0.1:{port}'
        def do_GET(self):
            try:
                u=urlsplit(self.path)
                if self.headers.get('Host')!=f'127.0.0.1:{port}':return self.reply(403,{'error':'invalid host'})
                if u.path in ('/','/admin','/admin/'):
                    return self.reply(200,ADMIN.replace('TOKEN',json.dumps(token)),'text/html; charset=utf-8')
                if not self.allowed():return self.reply(403,{'error':'拒绝跨站管理请求'})
                if u.path=='/api/documents':return self.reply(200,manager.list())
                if u.path=='/api/document':
                    q=parse_qs(u.query);return self.reply(200,manager.get(q['id'][0],int(q['revision'][0]) if 'revision'in q else None))
                self.reply(404,{'error':'not found'})
            except (VaultError,KeyError,ValueError) as e:self.reply(400,{'error':str(e)})
        def do_POST(self):
            if not self.allowed(True):return self.reply(403,{'error':'拒绝跨站管理请求'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=5_000_000:raise VaultError('请求为空或超过 5 MB')
                data=json.loads(self.rfile.read(length))
                if self.path=='/api/save':return self.reply(200,manager.save(data))
                if self.path=='/api/publish':return self.reply(200,manager.publish(data['id'],int(data['revision'])))
                self.reply(404,{'error':'not found'})
            except (VaultError,KeyError,ValueError) as e:self.reply(400,{'error':str(e)})
    return Handler


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--snapshot',required=True);p.add_argument('--site',required=True);p.add_argument('--port',type=int,default=8766);p.add_argument('--with-reader',action='store_true');a=p.parse_args()
    m=Manager(a.root,a.snapshot,a.site)
    if a.with_reader:
        reader=ThreadingHTTPServer(('127.0.0.1',8765),partial(ReaderHandler,directory=str(Path(a.site).resolve())))
        threading.Thread(target=reader.serve_forever,daemon=True).start()
    server=ThreadingHTTPServer(('127.0.0.1',a.port),handler(m,secrets.token_urlsafe(32),a.port))
    print(f'Vault 管理：http://127.0.0.1:{a.port}/admin/',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
