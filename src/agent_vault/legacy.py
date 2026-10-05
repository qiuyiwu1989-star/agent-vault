"""Lossless historical import into review-only tables, separate from strict v1 publication."""
import argparse
import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
from .core import Vault, VaultError, page

PREFIX = 'vault-migration-snapshot/'
ALIASES = {'date':('日期','分析日期','榨取日期'), 'author':('作者','讲者'),
           'source':('来源',), 'input_type':('输入类型',), 'tags':('标签',),
           'category':('类型',), 'summary':('一句话','一句话总结','核心判断')}


class Title(HTMLParser):
    def __init__(self):
        super().__init__(); self.inside=False; self.parts=[]
    def handle_starttag(self, tag, attrs):
        if tag == 'title': self.inside=True
    def handle_endtag(self, tag):
        if tag == 'title': self.inside=False
    def handle_data(self, data):
        if self.inside: self.parts.append(data)


def metadata(text, filename, kind):
    """Extract explicit evidence only; do not coerce author teams/types into author/tags."""
    values, evidence, issues = {}, {}, []
    if kind == 'html':
        parser=Title();parser.feed(text)
        if parser.parts:
            values['title']=''.join(parser.parts).strip()
            evidence['title']={'method':'html-title'}
        else: issues.append('missing:title')
        return dict(values=values,evidence=evidence,issues=issues)
    lines=text.splitlines()
    for index,line in enumerate(lines):
        if re.match(r'^#\s+\S',line):
            values['title']=re.sub(r'^#\s+','',line)
            evidence['title']={'line':index+1,'raw':line};break
    # Metadata lives before the first content section; retain code-fenced metadata too.
    header=[]
    for index,line in enumerate(lines[:100]):
        if re.match(r'^#{2,6}\s',line) and not any(k in line for k in ('元信息','基本信息','书籍信息')):
            break
        header.append((index,line))
    for key,aliases in ALIASES.items():
        matches=[]
        for index,line in header:
            norm=line.replace('**','').strip()
            norm=re.sub(r'^[-*]\s+','',norm)
            for alias in aliases:
                m=re.fullmatch(re.escape(alias)+r'\s*[：:]\s*(.+)',norm)
                if m:
                    matches.append({'value':m.group(1).strip(),'line':index+1,'raw':line})
        if matches:
            evidence[key]=matches
            distinct=list(dict.fromkeys(m['value'] for m in matches))
            if len(distinct)==1: values[key]=distinct[0]
            else: issues.append('conflicting:'+key)
    if 'date' not in values and not any(i=='conflicting:date' for i in issues):
        m=re.match(r'^(\d{4}-\d{2}-\d{2})',filename)
        if m:
            values['date']=m.group(1);evidence['date']={'method':'filename','raw':filename}
    if 'date' in values:
        try: date.fromisoformat(values['date'])
        except ValueError: issues.append('invalid:date')
    for key in ('title','date','source','author','tags','summary'):
        if key not in values: issues.append('missing:'+key)
    if len(values.get('summary',''))>60: issues.append('legacy_summary_over_60_preserved')
    if 'tags' in values:
        values['tags']=re.split(r'\s*[/、,，]\s*',values['tags'])
    return dict(values=values,evidence=evidence,issues=issues)


def import_review(review, root, actor):
    if not actor.strip(): raise VaultError('actor required')
    review=Path(review)
    report=json.loads((review/'report.json').read_text())
    for key in ('checksum_mismatches','missing_entries','duplicate_entries','unlisted_files'):
        if report[key]: raise VaultError('unresolved audit problem: '+key)
    manifest=json.loads((review/'preservation.json').read_text())
    files={}
    for item in manifest:
        path=PurePosixPath(item['path']); digest=item['sha256']
        if path.is_absolute() or '..' in path.parts or item['path'] in files or not re.fullmatch('[a-f0-9]{64}',digest):
            raise VaultError('invalid preservation manifest')
        b=(review/'blobs'/digest).read_bytes()
        if len(b)!=item['bytes'] or hashlib.sha256(b).hexdigest()!=digest:
            raise VaultError('preserved blob mismatch: '+item['path'])
        files[item['path']]=b
    # Independently check inventory against preserved bytes; don't trust a hand-edited audit summary.
    inventory=json.loads(files[PREFIX+'inventory.json'])
    seen=set()
    for item in inventory['items']:
        name=item['package_path'];b=files.get(name)
        if name in seen or b is None or len(b)!=item['bytes'] or hashlib.sha256(b).hexdigest()!=item['sha256']:
            raise VaultError('inventory mismatch')
        seen.add(name)
    if len(seen)!=inventory['count'] or set(files)-seen!={PREFIX+'inventory.json'}:
        raise VaultError('inventory coverage mismatch')
    records=[]
    # Derive candidates from bytes rather than trusting the audit candidate list.
    for name,b in sorted(files.items()):
        if name.startswith(PREFIX+'source/vault-staging/') and name.endswith('.md') and PurePosixPath(name).name.upper()!='INDEX.MD':
            coll=name[len(PREFIX+'source/vault-staging/'):].split('/')[0];kind='markdown'
            if coll not in ('books','reading','digest'):continue
            rel=name[len(PREFIX+'source/vault-staging/'):]
            public=PREFIX+'published/vault/'+str(PurePosixPath(rel).with_suffix('.html'))
        elif name.startswith(PREFIX+'published/vault/html/') and name.endswith('.html') and name!=PREFIX+'published/vault/html/index.html':
            coll='html';kind='html';public=name;rel=name[len(PREFIX+'published/vault/'):]
        else: continue
        rec=metadata(b.decode('utf-8'),PurePosixPath(name).name,kind)
        rec.update(id='legacy-'+hashlib.sha256(name.encode()).hexdigest()[:24],source_path=name,
                   collection=coll,kind=kind,sha256=hashlib.sha256(b).hexdigest(),
                   old_url='/vault/'+str(PurePosixPath(rel).with_suffix('.html')) if kind=='markdown' else '/vault/'+rel,
                   published_path=public if public in files else None,status='needs_review')
        if kind=='markdown':
            replica=PREFIX+'published/vault/'+rel
            rec['replica_path']=replica if replica in files else None
            rec['replica_differs']=replica in files and files[replica]!=b
        records.append(rec)
    v=Vault(root);snapshot=report['archive_sha256']
    with v.connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS legacy_snapshots(id TEXT PRIMARY KEY,actor TEXT NOT NULL,record TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS legacy_blobs(sha256 TEXT PRIMARY KEY,content BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS legacy_files(snapshot TEXT NOT NULL,path TEXT NOT NULL,sha256 TEXT NOT NULL,PRIMARY KEY(snapshot,path));
        CREATE TABLE IF NOT EXISTS legacy_documents(snapshot TEXT NOT NULL,id TEXT NOT NULL,record TEXT NOT NULL,PRIMARY KEY(snapshot,id));
        ''')
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT record FROM legacy_snapshots WHERE id=?',(snapshot,)).fetchone()
        if old: return dict(snapshot=snapshot,documents=len(records),unchanged=True)
        # Only content material, never imported operational scripts or skills, goes into the Vault DB.
        for name,b in files.items():
            if not name.startswith((PREFIX+'source/',PREFIX+'published/')):continue
            digest=hashlib.sha256(b).hexdigest()
            db.execute('INSERT OR IGNORE INTO legacy_blobs VALUES(?,?)',(digest,b))
            db.execute('INSERT INTO legacy_files VALUES(?,?,?)',(snapshot,name,digest))
        for r in records:
            db.execute('INSERT INTO legacy_documents VALUES(?,?,?)',(snapshot,r['id'],json.dumps(r,ensure_ascii=False)))
        db.execute('INSERT INTO legacy_snapshots VALUES(?,?,?)',(snapshot,actor,json.dumps({'documents':len(records)})))
        v.event(db,'import_legacy_review',{'snapshot':snapshot,'documents':len(records)},actor)
    return dict(snapshot=snapshot,documents=len(records),unchanged=False)


def review_export(root,snapshot,output):
    v=Vault(root);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    with v.connect() as db:
        rows=db.execute('SELECT record FROM legacy_documents WHERE snapshot=? ORDER BY id',(snapshot,)).fetchall()
        if not rows: raise VaultError('snapshot not found')
        records=[json.loads(r['record']) for r in rows]
        listings=[]
        for r in records:
            b=db.execute('SELECT b.content FROM legacy_files f JOIN legacy_blobs b ON f.sha256=b.sha256 WHERE f.snapshot=? AND f.path=?',(snapshot,r['source_path'])).fetchone()['content']
            title=r['values'].get('title',PurePosixPath(r['source_path']).name)
            # Text-only source view. No imported scripts, external resource loads or raw HTML execution.
            body='<a href="index.html">返回审阅清单</a><h1>'+html.escape(title)+'</h1><p>待审阅；原文保全视图</p>'
            body+='<pre>'+html.escape(b.decode('utf-8'))+'</pre>'
            (out/(r['id']+'.html')).write_text(page(title,body))
            listings.append('<article><a href="'+r['id']+'.html">'+html.escape(title)+'</a><p>'+html.escape(r['collection']+' / '+r['kind'])+'</p><small>'+html.escape('; '.join(r['issues']))+'</small></article>')
        (out/'index.html').write_text(page('历史成果待审阅','<h1>历史成果待审阅</h1><p>'+str(len(records))+' 份；未发布</p>'+''.join(listings)))
        (out/'candidates.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    return dict(documents=len(records),path=str(out.resolve()/'index.html'))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True)
    sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('import');p.add_argument('review');p.add_argument('--actor',required=True)
    p=sub.add_parser('preview');p.add_argument('snapshot');p.add_argument('--out',required=True)
    a=ap.parse_args()
    r=import_review(a.review,a.root,a.actor) if a.command=='import' else review_export(a.root,a.snapshot,a.out)
    print(json.dumps(r,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
