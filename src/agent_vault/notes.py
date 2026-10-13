"""Independent Markdown notes; private capture references and optimistic versions."""
import re
from uuid import UUID
from datetime import datetime, timezone
from psycopg2.extras import Json

class Conflict(Exception):
    def __init__(self, current): self.current = current

def init(connect):
    with connect() as db, db.cursor() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS zhuazhua_notes (
            id uuid PRIMARY KEY, data jsonb NOT NULL, version integer NOT NULL DEFAULT 1,
            created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now())''')

def validate(data):
    if not isinstance(data, dict): raise ValueError('笔记格式无效')
    if not isinstance(data.get('id'),str): raise ValueError('笔记 ID 无效')
    result = {'id':str(UUID(data['id']))}
    for key, limit in [('title',512),('markdown',500000),('tags',4000),('sourceURL',2048)]:
        value=data.get(key,'')
        if not isinstance(value,str) or len(value)>limit or '\x00' in value: raise ValueError('字段长度无效：'+key)
        result[key]=value
    if not result['markdown'].strip(): raise ValueError('笔记内容不能为空')
    for key in ('collectedAt','modifiedAt'):
        value=data.get(key)
        if not isinstance(value,str): raise ValueError('缺少时间')
        try:
            stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
            if not stamp.tzinfo: raise ValueError()
        except Exception: raise ValueError('时间格式无效') from None
        result[key]=stamp.astimezone(timezone.utc).isoformat()
    attachments=data.get('attachments',[])
    if not isinstance(attachments,list) or len(attachments)>100 or any(not isinstance(v,str) or not re.fullmatch('[a-f0-9]{64}',v) for v in attachments): raise ValueError('附件格式无效')
    result['attachments']=list(dict.fromkeys(attachments))
    referenced=re.findall(r'/api/zhuazhua/image/([a-f0-9]{64})',result['markdown'])
    result['attachments']=list(dict.fromkeys(result['attachments']+referenced))
    if len(result['attachments'])>100: raise ValueError('附件过多')
    version=data.get('version',0)
    if type(version) is not int or version<0: raise ValueError('笔记版本无效')
    return result,version

def present(data, version):
    return dict(data,kind='note',version=version)

def detail(connect, identity):
    identity=str(UUID(identity))
    with connect() as db, db.cursor() as c:
        c.execute('SELECT data,version FROM zhuazhua_notes WHERE id=%s',(identity,))
        row=c.fetchone()
    return present(*row) if row else None

def upsert(connect, data):
    item,version=validate(data)
    with connect() as db, db.cursor() as c:
        c.execute('SELECT pg_advisory_xact_lock(%s)',(UUID(item['id']).int % (2**63-1),))
        c.execute('SELECT data,version FROM zhuazhua_notes WHERE id=%s FOR UPDATE',(item['id'],))
        old=c.fetchone()
        if old: item['collectedAt']=old[0]['collectedAt']
        # Exact retries after lost responses are idempotent, including immutable dates.
        if old and old[0]==item and version in (old[1],old[1]-1): return present(*old)
        if (old and version!=old[1]) or (not old and version!=0):
            raise Conflict(present(*old) if old else None)
        if item['attachments']:
            c.execute('SELECT digest FROM zhuazhua_captures WHERE digest=ANY(%s)',(item['attachments'],))
            if {r[0] for r in c.fetchall()}!=set(item['attachments']): raise ValueError('附件尚未上传，请先保存图片')
        next_version=(old[1] if old else 0)+1
        c.execute('''INSERT INTO zhuazhua_notes(id,data,version) VALUES(%s,%s,%s)
            ON CONFLICT(id) DO UPDATE SET data=EXCLUDED.data,version=EXCLUDED.version,updated_at=now()''',
            (item['id'],Json(item),next_version))
    return present(item,next_version)

def listing(connect, query):
    q=query.get('q',[''])[0][:300].lower()
    day=query.get('day',[''])[0]
    if day and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day): raise ValueError('日期无效')
    limit=max(1,min(60,int(query.get('limit',['24'])[0])))
    offset=max(0,min(100000,int(query.get('offset',['0'])[0])))
    with connect() as db, db.cursor() as c:
        c.execute('''SELECT id::text,data->>'title',left(data->>'markdown',240),data->>'tags',
            data->>'collectedAt',data->>'modifiedAt',version FROM zhuazhua_notes
            WHERE (%s='' OR strpos(lower(data::text),%s)>0)
            AND (%s='' OR to_char((data->>'collectedAt')::timestamptz AT TIME ZONE 'Asia/Shanghai','YYYY-MM-DD')=%s)
            ORDER BY (data->>'collectedAt')::timestamptz DESC,id LIMIT %s OFFSET %s''',(q,q,day,day,limit+1,offset))
        rows=c.fetchall()
    keys=('id','title','excerpt','tags','collectedAt','modifiedAt','version')
    return {'items':[dict(zip(keys,row),kind='note') for row in rows[:limit]],'more':len(rows)>limit}
