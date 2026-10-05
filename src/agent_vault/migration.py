"""Read-only snapshot audit and lossless quarantine. Never execute imported code."""
import argparse
import hashlib
import html
import json
import posixpath
import tarfile
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from .core import parse, VaultError, page


class References(HTMLParser):
    def __init__(self):
        super().__init__(); self.resources = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('src', 'href'):
            if key in attrs and (key == 'src' or tag == 'link'):
                self.resources.append(attrs[key])


def audit(archive, output):
    output = Path(output)
    with tarfile.open(archive, 'r:gz') as tar:
        files = {}
        total = 0
        for member in tar:
            p = PurePosixPath(member.name)
            if p.is_absolute() or '..' in p.parts or member.issym() or member.islnk():
                raise VaultError('unsafe archive member: ' + member.name)
            if member.isdir(): continue
            if not member.isfile() or member.name in files:
                raise VaultError('unsupported or duplicate archive member')
            total += member.size
            if total > 100_000_000 or member.size > 20_000_000:
                raise VaultError('snapshot exceeds audit size limit')
            files[member.name] = tar.extractfile(member).read()
    prefix = 'vault-migration-snapshot/'
    inventory = json.loads(files[prefix + 'inventory.json'])
    mismatches, missing, duplicated = [], [], []
    seen = set()
    for item in inventory['items']:
        name = item['package_path']
        if name in seen: duplicated.append(name)
        seen.add(name)
        if name not in files: missing.append(name); continue
        b = files[name]
        if len(b) != item['bytes'] or hashlib.sha256(b).hexdigest() != item['sha256']:
            mismatches.append(name)
    unlisted = sorted(set(files)-seen-{prefix+'inventory.json'})
    candidates, counts, source_differences = [], {}, []
    for coll in ('books','reading','digest','html'):
        src = prefix+'source/vault-staging/'+coll+'/'
        pub = prefix+'published/vault/'+coll+'/'
        sources = [n for n in files if n.startswith(src) and n.endswith('.md') and PurePosixPath(n).name.upper() != 'INDEX.MD']
        pages = [n for n in files if n.startswith(pub) and n.endswith('.html') and n != pub+'index.html']
        counts[coll] = dict(source_markdown=len(sources), published_pages=len(pages))
        for name in sources:
            text = files[name].decode('utf-8')
            try:
                parse(text,PurePosixPath(name).name,coll); issues=[]
            except VaultError as e:
                issues=str(e).split('; ')
            server = pub+name[len(src):]
            if server not in files or files[name] != files[server]:
                source_differences.append(dict(source=name, server=server, status='missing' if server not in files else 'different'))
            candidates.append(dict(source=name,collection=coll,kind='markdown',sha256=hashlib.sha256(files[name]).hexdigest(),
                                   status='needs_compatibility' if issues else 'strict_valid',issues=issues))
        if coll == 'html':
            for name in pages:
                candidates.append(dict(source=name,collection=coll,kind='html',sha256=hashlib.sha256(files[name]).hexdigest(),
                                       status='preserved_html',issues=[]))
    broken, external = [], set()
    pubroot = prefix+'published/vault/'
    for name,b in files.items():
        if not name.startswith(pubroot) or not name.endswith('.html'): continue
        parser = References(); parser.feed(b.decode('utf-8'))
        for raw in parser.resources:
            u = urlsplit(raw)
            if u.scheme in ('data','javascript') or not u.path: continue
            if u.netloc and u.netloc != 'qiuyiwu.com': external.add(u.netloc); continue
            path = unquote(u.path)
            if path.startswith('/vault/'):
                target = pubroot+path[len('/vault/'):]
            elif path.startswith('/'):
                # Dependencies outside snapshot are not proven missing.
                external.add('outside-snapshot:'+path); continue
            else:
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name),path))
            if target not in files and target.rstrip('/')+'/index.html' not in files:
                broken.append(dict(page=name,reference=raw,resolved=target))
    report = dict(archive_sha256=hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
                  actual_files=len(files), declared_count=inventory.get('count'), inventory_entries=len(inventory['items']),
                  checksum_mismatches=mismatches,missing_entries=missing,duplicate_entries=duplicated,unlisted_files=unlisted,
                  collections=counts,source_replica_differences=source_differences,candidates=candidates,
                  missing_local_resources=broken,external_dependencies=sorted(external),
                  scope='Snapshot only; HTML preserved without execution; no live endpoint checks or credential scan.')
    # Preserve all bytes in content-addressed quarantine; never copy scripts into runtime or publish HTML.
    output.mkdir(parents=True,exist_ok=True)
    blobs=output/'blobs';blobs.mkdir(exist_ok=True)
    manifest=[]
    for name,b in files.items():
        digest=hashlib.sha256(b).hexdigest(); dest=blobs/digest
        if not dest.exists(): dest.write_bytes(b)
        elif dest.read_bytes()!=b: raise VaultError('quarantine blob mismatch')
        manifest.append(dict(path=name,sha256=digest,bytes=len(b)))
    (output/'preservation.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    body='<h1>Vault 迁移审阅</h1><p>仅本地静态清单；没有运行导入脚本或原始 HTML。</p>'
    body+='<p>实际文件 '+str(len(files))+'；清单条目 '+str(len(inventory['items']))+'；校验不符 '+str(len(mismatches))+'</p>'
    for coll,stat in counts.items():
        body+='<h2>'+coll+'</h2><p>'+html.escape(str(stat))+'</p>'
    for c in candidates:
        body+='<article><strong>'+html.escape(c['source'].split('/')[-1])+'</strong><p>'+html.escape(c['status'])+'</p><small>'+html.escape('; '.join(c['issues']))+'</small></article>'
    (output/'index.html').write_text(page('Vault 迁移审阅',body))
    return report


def main():
    ap=argparse.ArgumentParser();ap.add_argument('archive');ap.add_argument('--out',required=True)
    a=ap.parse_args();r=audit(a.archive,a.out)
    print(json.dumps({k:v for k,v in r.items() if k not in ('candidates','external_dependencies')},ensure_ascii=False,indent=2))
    return 1 if any(r[k] for k in ('checksum_mismatches','missing_entries','duplicate_entries','unlisted_files')) else 0


if __name__=='__main__':
    raise SystemExit(main())
