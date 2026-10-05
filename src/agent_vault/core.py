import hashlib
import html
import json
import re
import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

COLLECTIONS = ('books', 'reading', 'digest', 'html')
IDENTIFIER = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


class VaultError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def parse(text, filename, collection):
    """Strict v1 input; return one normalized representation for all consumers."""
    errors = []
    if collection not in COLLECTIONS:
        errors.append('unknown collection')
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md', filename)
    if not match:
        errors.append('filename must be YYYY-MM-DD-lowercase-slug.md')
    lines = text.splitlines()
    if not lines or not re.match(r'^# \S', lines[0]):
        errors.append('first line must be one H1 title')
    meta = {}
    i = 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines):
        m = re.fullmatch(r'- \*\*([^*]+)\*\*：(.*)', lines[i])
        if not m:
            break
        key, value = m.group(1), m.group(2).strip()
        if key in meta:
            errors.append('duplicate metadata: ' + key)
        meta[key] = value
        i += 1
    required = ['日期', '来源', '标签', '一句话']
    if collection == 'books':
        required += ['作者', '类型']
    for key in required:
        if not meta.get(key):
            errors.append('missing or empty field: ' + key)
    if collection == 'reading' and not (meta.get('作者') or meta.get('讲者')):
        errors.append('reading requires 作者 or 讲者')
    try:
        date.fromisoformat(meta.get('日期', ''))
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', meta['日期']):
            raise ValueError()
        if match and match.group(1) != meta['日期']:
            errors.append('filename date and metadata date differ')
    except ValueError:
        errors.append('invalid calendar date')
    if len(meta.get('一句话', '')) > 60:
        errors.append('一句话 exceeds 60 characters')
    tags = meta.get('标签', '').split(' / ')
    if not 2 <= len(tags) <= 4 or any(not x.strip() for x in tags) or len(set(tags)) != len(tags):
        errors.append('标签 requires 2–4 distinct tags separated by " / "')
    body = '\n'.join(lines[i:]).strip()
    body = re.sub(r'^---\s*\n', '', body).strip()
    if not body.startswith('## '):
        errors.append('body must start with H2')
    fenced = False
    for line in body.splitlines():
        if line.startswith('```'):
            fenced = not fenced
        elif not fenced and re.match(r'^#\s', line):
            errors.append('body contains another H1')
    if errors:
        raise VaultError('; '.join(errors))
    return dict(schema_version=1, title=lines[0][2:].strip(), date=meta['日期'],
                source=meta['来源'], author=meta.get('作者') or meta.get('讲者', ''),
                tags=tags, summary=meta['一句话'], collection=collection,
                filename=filename, body=body, metadata=meta)


def render_body(body):
    """Safe, deliberately small Markdown subset; raw HTML is displayed as text."""
    out, code = [], False
    for line in body.splitlines():
        if line.startswith('```'):
            out.append('</code></pre>' if code else '<pre><code>')
            code = not code
            continue
        escaped = html.escape(line)
        if code:
            out.append(escaped + '\n')
        elif re.match(r'^#{2,6} ', line):
            level = len(line.split(' ')[0])
            out.append(f'<h{level}>{html.escape(line[level+1:])}</h{level}>')
        elif line:
            out.append('<p>' + escaped + '</p>')
    if code:
        out.append('</code></pre>')
    return '\n'.join(out)


def page(title, body):
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + html.escape(title) + '</title><style>'
            'body{max-width:850px;margin:48px auto;padding:0 24px;background:#fbfaf6;color:#221e1a;'
            'font:17px/1.8 system-ui}a{color:#8e4231}article{padding:20px 0;border-bottom:1px solid #cfc7b6}'
            'pre{white-space:pre-wrap}small{color:#6e665c}</style><body>' + body + '</body></html>')


class Vault:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'vault.sqlite3'
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS revisions(
              id TEXT NOT NULL, revision INTEGER NOT NULL, filename TEXT NOT NULL,
              collection TEXT NOT NULL, markdown TEXT NOT NULL, record TEXT NOT NULL,
              digest TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL, created TEXT NOT NULL,
              PRIMARY KEY(id, revision));
            CREATE TABLE IF NOT EXISTS heads(id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
              collection TEXT NOT NULL, filename TEXT NOT NULL, UNIQUE(collection, filename));
            CREATE TABLE IF NOT EXISTS published(id TEXT PRIMARY KEY, revision INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              action TEXT NOT NULL, detail TEXT NOT NULL, actor TEXT NOT NULL, created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS releases(id TEXT PRIMARY KEY, manifest TEXT NOT NULL, created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            ''')

    def connect(self):
        db = sqlite3.connect(self.db, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def event(db, action, detail, actor):
        db.execute('INSERT INTO events(action,detail,actor,created) VALUES(?,?,?,?)',
                   (action, json.dumps(detail, ensure_ascii=False), actor, now()))

    def submit(self, path, collection, actor, doc_id=None, expected=0, reason='initial submission'):
        if not actor.strip() or not reason.strip():
            raise VaultError('actor and reason are required')
        path = Path(path)
        text = path.read_text(encoding='utf-8')
        record = parse(text, path.name, collection)
        digest = hashlib.sha256(text.encode()).hexdigest()
        if doc_id and not IDENTIFIER.fullmatch(doc_id):
            raise VaultError('invalid document id')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            head = db.execute('SELECT * FROM heads WHERE id=?', (doc_id,)).fetchone() if doc_id else db.execute(
                'SELECT * FROM heads WHERE collection=? AND filename=?', (collection, path.name)).fetchone()
            if head:
                previous = db.execute('SELECT * FROM revisions WHERE id=? AND revision=?',
                                      (head['id'], head['revision'])).fetchone()
                if head['collection'] != collection or head['filename'] != path.name:
                    raise VaultError('collection/filename is immutable; migration requires a separate operation')
                if previous['digest'] == digest:
                    return dict(id=head['id'], revision=head['revision'], unchanged=True)
                if expected != head['revision']:
                    raise VaultError(f'version conflict: expected {expected}, current {head["revision"]}')
                doc_id, revision = head['id'], head['revision'] + 1
            else:
                if expected != 0:
                    raise VaultError('new document requires expected revision 0')
                doc_id, revision = doc_id or str(uuid.uuid4()), 1
            db.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (doc_id, revision, path.name, collection, text, json.dumps(record, ensure_ascii=False),
                        digest, actor, reason, now()))
            db.execute('INSERT INTO heads VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision', (doc_id, revision, collection, path.name))
            self.event(db, 'submit', dict(id=doc_id, revision=revision), actor)
            return dict(id=doc_id, revision=revision, unchanged=False, state='draft')

    def get(self, doc_id, revision=None):
        with self.connect() as db:
            row = db.execute('SELECT r.* FROM revisions r JOIN heads h ON r.id=h.id AND r.revision=h.revision WHERE r.id=?',
                             (doc_id,)).fetchone() if revision is None else db.execute(
                'SELECT * FROM revisions WHERE id=? AND revision=?', (doc_id, revision)).fetchone()
            if row is None:
                raise VaultError('document/revision not found')
            return dict(row)

    def list(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT h.*,p.revision AS published_revision FROM heads h LEFT JOIN published p ON h.id=p.id ORDER BY h.collection,h.filename')]

    def publish(self, doc_id, revision, actor):
        """Build complete immutable release before atomically changing active DB pointer."""
        if not actor.strip():
            raise VaultError('actor required')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            head = db.execute('SELECT revision FROM heads WHERE id=?', (doc_id,)).fetchone()
            if not head or head['revision'] != revision:
                raise VaultError('publish requires current explicit revision')
            selected = {r['id']: r['revision'] for r in db.execute('SELECT * FROM published')}
            selected[doc_id] = revision
            release = self._build(db, selected)
            db.execute('INSERT OR REPLACE INTO published VALUES(?,?)', (doc_id, revision))
            db.execute('INSERT INTO releases VALUES(?,?,?)', (release, json.dumps(selected), now()))
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', ('active_release', release))
            self.event(db, 'publish', dict(id=doc_id, revision=revision, release=release), actor)
            return dict(release=release, path=str(self.root / 'releases' / release), documents=len(selected))

    def _build(self, db, selected):
        release = str(uuid.uuid4())
        target = self.root / 'releases' / release
        target.mkdir(parents=True)
        records = []
        for doc_id, revision in sorted(selected.items()):
            row = db.execute('SELECT * FROM revisions WHERE id=? AND revision=?', (doc_id, revision)).fetchone()
            r = parse(row['markdown'], row['filename'], row['collection'])
            r.update(id=doc_id, revision=revision)
            directory = target / r['collection']
            directory.mkdir(exist_ok=True)
            url = r['collection'] + '/' + doc_id + '.html'
            content = '<a href="index.html">返回集合</a><h1>' + html.escape(r['title']) + '</h1>'
            content += '<small>' + html.escape(r['date'] + ' · ' + r['author']) + '</small>'
            content += '<p>来源：' + html.escape(r['source']) + '</p>' + render_body(r['body'])
            (target / url).write_text(page(r['title'], content), encoding='utf-8')
            # Legacy filename URL remains an equivalent page, not an unsafe redirect.
            (directory / Path(r['filename']).with_suffix('.html').name).write_text(page(r['title'], content), encoding='utf-8')
            records.append({k: r[k] for k in ('id','revision','collection','title','date','source','author','tags','summary')} | {'url': url})
        cards = []
        for coll in COLLECTIONS:
            items = [r for r in records if r['collection'] == coll]
            directory = target / coll
            directory.mkdir(exist_ok=True)
            listing = '<a href="../index.html">全部成果</a><h1>' + coll + '</h1>'
            for r in sorted(items, key=lambda x: (x['date'], x['id']), reverse=True):
                listing += '<article><a href="' + r['id'] + '.html">' + html.escape(r['title']) + '</a><p>' + html.escape(r['summary']) + '</p></article>'
            (directory / 'index.html').write_text(page(coll, listing), encoding='utf-8')
            cards.append(f'<article><a href="{coll}/index.html">{coll}</a> · {len(items)}</article>')
        (target / 'index.html').write_text(page('Vault', '<h1>Vault</h1><p>' + str(len(records)) + ' 份已发布成果</p>' + ''.join(cards)), encoding='utf-8')
        (target / 'catalog.json').write_text(json.dumps(dict(schema_version=1, items=records), ensure_ascii=False, indent=2), encoding='utf-8')
        return release

    def active(self):
        with self.connect() as db:
            r = db.execute("SELECT value FROM settings WHERE key='active_release'").fetchone()
            return dict(release=r['value'], path=str(self.root / 'releases' / r['value'])) if r else None

    def rollback(self, release, actor):
        if not actor.strip():
            raise VaultError('actor required')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            r = db.execute('SELECT manifest FROM releases WHERE id=?', (release,)).fetchone()
            if not r or not (self.root / 'releases' / release / 'catalog.json').is_file():
                raise VaultError('complete release not found')
            db.execute('DELETE FROM published')
            db.executemany('INSERT INTO published VALUES(?,?)', json.loads(r['manifest']).items())
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', ('active_release', release))
            self.event(db, 'rollback', dict(release=release), actor)
            return dict(release=release)
