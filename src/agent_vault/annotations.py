"""Owner-scoped annotation service; Vault is the first registered document resolver."""
import uuid
from psycopg2.extras import Json
from .knowledge import reanchor

class AnnotationError(ValueError):
    pass

class AnnotationStore:
    def __init__(self, connect, resolvers):
        self.connect=connect
        self.resolvers=resolvers
    def init(self):
        with self.connect() as db,db.cursor() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS web_annotations (
              id text PRIMARY KEY, namespace text NOT NULL, document_id text NOT NULL,
              owner_id text NOT NULL, record jsonb NOT NULL, version integer NOT NULL DEFAULT 1,
              deleted_at timestamptz, created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now());
              CREATE INDEX IF NOT EXISTS web_annotations_owner_document
                ON web_annotations(owner_id,namespace,document_id) WHERE deleted_at IS NULL;''')
    def document(self, namespace, document_id):
        if namespace not in self.resolvers:raise AnnotationError('未注册的文档模块')
        try:d=self.resolvers[namespace](document_id)
        except ValueError as e:raise AnnotationError('文档不存在或不可批注') from e
        if not d or 'text' not in d or 'hash' not in d:raise AnnotationError('文档不存在或不可批注')
        return d
    def list(self, owner, namespace, document_id):
        if not owner:raise AnnotationError('未登录')
        doc=self.document(namespace,document_id)
        with self.connect() as db,db.cursor() as c:
            c.execute('''SELECT id,record,version,created_at::text,updated_at::text
              FROM web_annotations WHERE owner_id=%s AND namespace=%s AND document_id=%s
              AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT 500''',(owner,namespace,document_id))
            return [dict(id=ident,**record,version=v,createdAt=created,updatedAt=updated,anchor=reanchor(record,doc)) for ident,record,v,created,updated in c.fetchall()]
    def create(self, owner, namespace, document_id, data):
        if not owner:raise AnnotationError('未登录')
        doc=self.document(namespace,document_id)
        start,end,quote=data.get('start'),data.get('end'),data.get('quote')
        comment=data.get('comment','')
        if type(start)!=int or type(end)!=int or not 0<=start<end<=len(doc['text']) or end-start>8000 or doc['text'][start:end]!=quote or data.get('contentRevision')!=doc['hash']:raise AnnotationError('正文或划线位置已变化，请重新选择')
        if not isinstance(comment,str) or len(comment)>10000:raise AnnotationError('笔记过长')
        record=dict(start=start,end=end,quote=quote,prefix=doc['text'][max(0,start-40):start],suffix=doc['text'][end:end+40],content_hash=doc['hash'],comment=comment,visibility='private')
        ident=str(uuid.uuid4())
        with self.connect() as db,db.cursor() as c:
            c.execute('INSERT INTO web_annotations(id,namespace,document_id,owner_id,record) VALUES(%s,%s,%s,%s,%s)',(ident,namespace,document_id,owner,Json(record)))
        return next(item for item in self.list(owner,namespace,document_id) if item['id']==ident)
    def update(self, owner, namespace, document_id, ident, data):
        if not owner:raise AnnotationError('未登录')
        comment=data.get('comment');version=data.get('expected')
        if not isinstance(comment,str) or len(comment)>10000 or type(version)!=int:raise AnnotationError('笔记内容或版本无效')
        self.document(namespace,document_id)
        with self.connect() as db,db.cursor() as c:
            c.execute('''UPDATE web_annotations SET record=jsonb_set(record,'{comment}',%s::jsonb),
              version=version+1,updated_at=now() WHERE id=%s AND owner_id=%s AND namespace=%s
              AND document_id=%s AND version=%s AND deleted_at IS NULL RETURNING id''',
              (Json(comment),ident,owner,namespace,document_id,version))
            if not c.fetchone():raise AnnotationError('笔记已变化或无权编辑，请刷新后重试')
        return next(item for item in self.list(owner,namespace,document_id) if item['id']==ident)
