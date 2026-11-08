"""Owner-scoped private archives. No implicit production connection or publication."""
import hashlib
import json
import uuid
from contextlib import contextmanager
from psycopg2.extras import Json


class ArchiveError(ValueError):
    pass


class ValidationError(ArchiveError):
    def __init__(self, report):
        self.report = report
        super().__init__('invalid archive payload')


class Conflict(ArchiveError):
    pass


class NotFound(ArchiveError):
    pass


class ArchiveStore:
    def __init__(self, connect):
        self.connect = connect

    @contextmanager
    def _connection(self):
        db = self.connect()
        try:
            with db:
                yield db
        finally:
            db.close()

    def init(self):
        with self._connection() as db, db.cursor() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS archive_contents (
                id text PRIMARY KEY, owner text NOT NULL, revision integer NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
                CREATE INDEX IF NOT EXISTS archive_owner ON archive_contents(owner);
                CREATE TABLE IF NOT EXISTS archive_revisions (
                id text NOT NULL REFERENCES archive_contents(id), revision integer NOT NULL,
                record jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY(id,revision));
                CREATE TABLE IF NOT EXISTS archive_requests (
                owner text NOT NULL, request_id text NOT NULL, fingerprint text NOT NULL,
                response jsonb NOT NULL, PRIMARY KEY(owner,request_id));''')

    @staticmethod
    def _identity(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 160:
            raise ArchiveError('invalid trusted identity or request id')
        return value

    @staticmethod
    def _lock(c, value):
        n = int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], 'big', signed=True)
        c.execute('SELECT pg_advisory_xact_lock(%s)', (n,))

    @staticmethod
    def _result(c, owner, ident, revision=None):
        c.execute('''SELECT d.id,r.revision,r.record,d.created_at::text,r.created_at::text
            FROM archive_contents d JOIN archive_revisions r ON r.id=d.id
            AND r.revision=COALESCE(%s,d.revision) WHERE d.id=%s AND d.owner=%s''',
                  (revision, ident, owner))
        row = c.fetchone()
        if not row:
            raise NotFound('archive not found')
        return dict(zip(('id', 'revision', 'record', 'created_at', 'updated_at'), row))

    def read(self, owner, id, revision=None):
        self._identity(owner)
        self._identity(id)
        if revision is not None and (type(revision) is not int or revision < 1):
            raise ArchiveError('invalid revision')
        with self._connection() as db, db.cursor() as c:
            return self._result(c, owner, id, revision)

    def search(self, owner, query='', limit=50):
        self._identity(owner)
        if not isinstance(query, str) or len(query) > 1000 or type(limit) is not int or not 1 <= limit <= 100:
            raise ArchiveError('invalid search parameters')
        with self._connection() as db, db.cursor() as c:
            c.execute('''SELECT d.id,r.revision,jsonb_build_object(
                'type',r.record->'type','title',r.record->'title',
                'body',left(COALESCE(NULLIF(r.record->>'body',''),
                  (SELECT string_agg(s->>'text',' ') FROM jsonb_array_elements(COALESCE(r.record->'sections','[]'::jsonb)) s),''),500),
                'tags',r.record->'tags','visibility','private'),d.created_at::text,r.created_at::text
                FROM archive_contents d JOIN archive_revisions r ON r.id=d.id AND r.revision=d.revision
                WHERE d.owner=%s AND (%s='' OR strpos(lower(COALESCE(r.record->>'title','')||' '||COALESCE(r.record->>'body','')||' '||COALESCE((SELECT string_agg(s->>'text',' ') FROM jsonb_array_elements(COALESCE(r.record->'sections','[]'::jsonb)) s),'')) ,lower(%s))>0)
                ORDER BY d.updated_at DESC,d.id LIMIT %s''', (owner, query, query, limit))
            return [dict(zip(('id','revision','record','created_at','updated_at'), row), summary_only=True) for row in c.fetchall()]

    def create(self, owner, actor, payload, request_id):
        return self._write(owner, actor, payload, request_id)

    def revise(self, owner, actor, id, expected_revision, payload, request_id):
        self._identity(id)
        if type(expected_revision) is not int or expected_revision < 1:
            raise ArchiveError('expected_revision must be a positive integer')
        return self._write(owner, actor, payload, request_id, id, expected_revision)

    def _write(self, owner, actor, payload, request_id, ident=None, expected=None):
        from .archive_validation import validate
        for value in (owner, actor, request_id):
            self._identity(value)
        report = validate(payload, stage='receive')
        if not report.get('valid'):
            raise ValidationError(report)
        if not isinstance(payload, dict) or any(k in payload for k in ('owner','actor')):
            raise ArchiveError('trusted identities cannot be supplied in payload')
        fingerprint = hashlib.sha256(json.dumps([actor, ident, expected, payload], sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        with self._connection() as db, db.cursor() as c:
            self._lock(c, json.dumps([owner, request_id]))
            c.execute('SELECT fingerprint,response FROM archive_requests WHERE owner=%s AND request_id=%s', (owner, request_id))
            old = c.fetchone()
            if old:
                if old[0] != fingerprint:
                    raise Conflict('request id reused for a different operation')
                return old[1]
            if ident is None:
                ident = str(uuid.uuid4()); revision = 1
                c.execute('INSERT INTO archive_contents(id,owner,revision) VALUES(%s,%s,%s)', (ident,owner,revision))
            else:
                c.execute('SELECT revision FROM archive_contents WHERE id=%s AND owner=%s FOR UPDATE', (ident,owner))
                row = c.fetchone()
                if not row:
                    raise NotFound('archive not found')
                if row[0] != expected:
                    raise Conflict('archive revision changed')
                revision = expected + 1
                c.execute('UPDATE archive_contents SET revision=%s,updated_at=now() WHERE id=%s', (revision,ident))
            record = dict(report['normalized'], visibility='private', actor=actor)
            c.execute('INSERT INTO archive_revisions(id,revision,record) VALUES(%s,%s,%s)', (ident,revision,Json(record)))
            result = self._result(c, owner, ident, revision)
            c.execute('INSERT INTO archive_requests(owner,request_id,fingerprint,response) VALUES(%s,%s,%s,%s)', (owner,request_id,fingerprint,Json(result)))
            return result
