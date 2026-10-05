"""Small local reader over preserved published pages. No migration or network writes."""
import argparse
import hashlib
import html
import json
import sqlite3
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from .core import VaultError

class Text(HTMLParser):
    def __init__(self):
        super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

SHELL='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vault · 知识成果库</title><style>
*{box-sizing:border-box}body{margin:0;background:#faf8f3;color:#272522;font:16px/1.7 system-ui,-apple-system,sans-serif}main{max-width:1100px;margin:auto;padding:44px 24px}header{display:flex;align-items:baseline;justify-content:space-between;gap:20px}h1{font-size:34px;margin:0}header span{color:#777067;font-size:13px}input{width:100%;margin:26px 0 18px;padding:15px 18px;border:1px solid #d7d1c4;border-radius:12px;background:white;font:inherit}nav{display:flex;gap:8px;flex-wrap:wrap}button{border:1px solid #d7d1c4;background:transparent;border-radius:22px;padding:8px 16px;font:inherit;cursor:pointer}button.on{background:#843f30;border-color:#843f30;color:white}#count{font-size:13px;color:#777067;margin:18px 0}#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:16px}article{background:white;border:1px solid #e2dcd0;border-radius:16px;padding:22px;display:flex;flex-direction:column}article small{color:#8c7763}article h2{font-size:19px;line-height:1.5;margin:12px 0}article p{font-size:14px;color:#746d65;margin:0 0 18px}a{color:#843f30;text-decoration:none}article>a{margin-top:auto}#empty{display:none;color:#777}footer{margin-top:36px;font-size:13px;color:#777067}@media(max-width:600px){main{padding:24px 16px}header{display:block}h1{font-size:28px}}
</style><main><header><h1>知识成果库</h1><span>本地版 · 2026-10-04 快照 · <a href="http://127.0.0.1:8766/admin/" target="_blank" rel="noopener">管理成果</a></span></header>
<input id="search" type="search" placeholder="搜索标题、作者或正文…" aria-label="搜索成果"><nav id="filters"></nav><p id="count" aria-live="polite"></p><section id="grid"></section><p id="empty">没有找到匹配成果，试试其他关键词。</p><footer>保留原有页面。在「管理成果」中编辑并发布到本地；内容不会自动同步到网站。</footer></main>
<script>
const names={all:'全部',books:'榨书档案',reading:'阅读档案',digest:'建造者日报',html:'分析与方案'};
let items=[],selected='all';const el=id=>document.getElementById(id);
function render(){const words=el('search').value.toLowerCase().trim().split(/\\s+/).filter(Boolean);const shown=items.filter(x=>(selected==='all'||x.collection===selected)&&words.every(w=>x.search.toLowerCase().includes(w)));el('grid').replaceChildren();for(const x of shown){const card=document.createElement('article');const meta=document.createElement('small');meta.textContent=names[x.collection]+(x.date?' · '+x.date:'');const h=document.createElement('h2');h.textContent=x.title;const p=document.createElement('p');p.textContent=x.summary;const a=document.createElement('a');a.href=x.url;a.textContent='打开阅读 ↗';a.target='_blank';a.rel='noopener';card.append(meta,h,p,a);el('grid').append(card)}el('count').textContent=shown.length+' / '+items.length+' 个成果';el('empty').style.display=shown.length?'none':'block';}
fetch('/catalog.json').then(r=>{if(!r.ok)throw Error();return r.json()}).then(data=>{items=data;for(const [key,label]of Object.entries(names)){const b=document.createElement('button');b.textContent=label+' '+items.filter(x=>key==='all'||x.collection===key).length;b.className=key==='all'?'on':'';b.onclick=()=>{selected=key;document.querySelectorAll('nav button').forEach(x=>x.classList.remove('on'));b.classList.add('on');render()};el('filters').append(b)}render()}).catch(()=>{el('count').textContent='目录加载失败，请重启本地阅读器。'});el('search').addEventListener('input',render);
</script></html>'''


def build(root,snapshot,out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(f'file:{Path(root).resolve()/"vault.sqlite3"}?mode=ro',uri=True);db.row_factory=sqlite3.Row
    try:
        records=[json.loads(r['record']) for r in db.execute('SELECT record FROM legacy_documents WHERE snapshot=?',(snapshot,))]
        if not records:raise VaultError('snapshot not found')
        prefix='vault-migration-snapshot/published/'
        for r in db.execute('SELECT f.path,f.sha256,b.content FROM legacy_files f JOIN legacy_blobs b ON f.sha256=b.sha256 WHERE f.snapshot=?',(snapshot,)):
            if not r['path'].startswith(prefix):continue
            rel=PurePosixPath(r['path'][len(prefix):])
            if rel.is_absolute() or '..' in rel.parts:raise VaultError('unsafe content path')
            if rel.suffix.lower() not in ('.html','.css','.js','.png','.jpg','.jpeg','.svg','.webp','.gif','.woff','.woff2','.pdf','.ico'):continue
            if hashlib.sha256(r['content']).hexdigest()!=r['sha256']:raise VaultError('blob mismatch')
            dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(r['content'])
        catalog=[]
        for r in records:
            if not r['published_path']:raise VaultError('missing published counterpart')
            rel=PurePosixPath(r['published_path'][len(prefix):]);p=out/rel
            if not p.is_file():raise VaultError('missing page')
            text=Text();text.feed(p.read_text())
            values=r['values'];title=values.get('title',rel.stem)
            catalog.append(dict(title=title,collection=r['collection'],date=values.get('date',''),summary=values.get('summary',''),url='/'+str(rel),search=' '.join([title,values.get('author','')]+text.parts)))
        catalog.sort(key=lambda x:(x['date'],x['title']),reverse=True)
        (out/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False))
        (out/'index.html').write_text(SHELL)
        # The common /vault/ return target also opens the unified reader.
        (out/'vault'/'index.html').write_text(SHELL)
        return dict(documents=len(catalog),directory=str(out))
    finally:db.close()


class Handler(SimpleHTTPRequestHandler):
    def list_directory(self,path):
        self.send_error(404);return None
    def do_GET(self):
        # Compatibility for old /html and /reading links, retaining query string.
        if self.path.startswith(('/html/','/reading/')):
            self.send_response(302);self.send_header('Location','/vault'+self.path);self.end_headers();return
        super().do_GET()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--snapshot',required=True);ap.add_argument('--out',required=True);ap.add_argument('--port',type=int,default=8765);ap.add_argument('--build-only',action='store_true')
    a=ap.parse_args();print(json.dumps(build(a.root,a.snapshot,a.out),ensure_ascii=False),flush=True)
    if not a.build_only:
        server=ThreadingHTTPServer(('127.0.0.1',a.port),partial(Handler,directory=str(Path(a.out).resolve())))
        print(f'http://127.0.0.1:{a.port}/',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()


if __name__=='__main__':main()
