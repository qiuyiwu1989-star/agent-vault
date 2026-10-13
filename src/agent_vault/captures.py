"""Private ZhuaZhua inbox. COS stores bytes; PostgreSQL stores metadata.
Device credentials authorize only these routes, never the rest of Vault.
"""
import base64, hashlib, hmac, io, json, os, re, time
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from PIL import Image, ImageOps
from psycopg2.extras import Json

from . import notes, telemetry

PREFIX = '/api/zhuazhua/'
LIMIT = 64 * 1024 * 1024

def init(connect):
    with connect() as db, db.cursor() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS zhuazhua_captures (
            digest text PRIMARY KEY, object_key text NOT NULL, mime text NOT NULL,
            size bigint NOT NULL, width integer NOT NULL, height integer NOT NULL,
            metadata jsonb NOT NULL, received_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now())''')
        c.execute('ALTER TABLE zhuazhua_captures ADD COLUMN IF NOT EXISTS thumbnail_key text')
    notes.init(connect)
    telemetry.init(connect)
    if os.environ.get('CAPTURE_COS_SECRET_ID'): client()

@lru_cache(maxsize=1)
def client():
    from qcloud_cos import CosConfig, CosS3Client
    return CosS3Client(CosConfig(Region=os.environ['CAPTURE_COS_REGION'],
        SecretId=os.environ['CAPTURE_COS_SECRET_ID'], SecretKey=os.environ['CAPTURE_COS_SECRET_KEY'],
        Scheme='https', Timeout=60))

@lru_cache(maxsize=1024)
def signed_image(key, window):
    # Reuse signatures briefly so browser caches survive refreshes. No public ACL.
    return client().get_presigned_url(Bucket=os.environ['CAPTURE_COS_BUCKET'],
        Key=key,Method='GET',Expired=900,Params={'response-cache-control':'private, max-age=600'})

def detail(connect, digest):
    with connect() as db, db.cursor() as c:
        c.execute('SELECT metadata,width,height,object_key FROM zhuazhua_captures WHERE digest=%s',(digest,))
        row=c.fetchone()
    if not row: return None
    return dict(digest=digest,**row[0],width=row[1],height=row[2],
        imageURL=PREFIX+'image/'+digest,displayURL=signed_image(row[3],int(time.time()//300)))

def note_images(connect, item):
    if not item: return item
    images=[]
    if item.get('attachments'):
        with connect() as db, db.cursor() as c:
            c.execute('SELECT digest,object_key,width,height FROM zhuazhua_captures WHERE digest=ANY(%s)',(item['attachments'],))
            rows=c.fetchall()
        images=[dict(digest=d,imageURL=PREFIX+'image/'+d,displayURL=signed_image(key,int(time.time()//300)),width=w,height=h) for d,key,w,h in rows]
    return dict(item,attachmentImages=images)

def device(handler):
    expected = os.environ.get('CAPTURE_DEVICE_SHA256', '')
    header = handler.headers.get('Authorization', '')
    return bool(expected) and header.startswith('Bearer ') and hmac.compare_digest(
        hashlib.sha256(header[7:].encode()).hexdigest(), expected)

def validate(data):
    if not isinstance(data, dict): raise ValueError('请求格式错误')
    encoded = data.get('image')
    if not isinstance(encoded, str) or len(encoded) > (LIMIT * 4 // 3 + 8): raise ValueError('图片超过 64 MB')
    try: raw = base64.b64decode(encoded, validate=True)
    except Exception: raise ValueError('图片编码错误') from None
    if not raw or len(raw) > LIMIT: raise ValueError('图片大小无效')
    digest = hashlib.sha256(raw).hexdigest()
    if data.get('digest') != digest: raise ValueError('图片校验不一致')
    try:
        with Image.open(io.BytesIO(raw)) as im:
            fmt, dimensions = im.format, im.size
            if dimensions[0]*dimensions[1] > 60_000_000: raise ValueError('图片像素过大')
            im.verify()
        mime = {'PNG':'image/png','JPEG':'image/jpeg','GIF':'image/gif','WEBP':'image/webp','TIFF':'image/tiff'}.get(fmt)
        if not mime: raise ValueError('不支持的图片格式')
    except Exception: raise ValueError('无法解码图片或图片尺寸过大') from None
    meta = {}
    for field, limit in [('name',512),('note',50000),('tags',4000),('ocr',200000),('sourceURL',2048)]:
        value = data.get(field, '')
        if not isinstance(value,str) or len(value)>limit: raise ValueError('字段长度无效：'+field)
        meta[field] = value
    for field in ('collectedAt','modifiedAt'):
        value = data.get(field)
        if not isinstance(value,str): raise ValueError('缺少时间')
        try:
            dt=datetime.fromisoformat(value.replace('Z','+00:00'))
            if not dt.tzinfo: raise ValueError()
        except Exception: raise ValueError('时间格式无效') from None
        meta[field]=dt.astimezone(timezone.utc).isoformat()
    return raw,digest,mime,dimensions,meta

def thumbnail(cos, bucket, digest, raw):
    key='zhuazhua/thumbnails/'+digest[:2]+'/'+digest+'.jpg'
    with Image.open(io.BytesIO(raw)) as image:
        image=ImageOps.exif_transpose(image)
        image.thumbnail((640,640))
        rgba=image.convert('RGBA')
        background=Image.new('RGBA',rgba.size,'white')
        background.alpha_composite(rgba)
        out=io.BytesIO();background.convert('RGB').save(out,'JPEG',quality=78,optimize=True)
    cos.put_object(Bucket=bucket,Key=key,Body=out.getvalue(),ContentType='image/jpeg',ACL='private')
    return key

def upload(connect, data):
    raw,digest,mime,(width,height),meta = validate(data)
    attachment_only=data.get('attachmentOnly',False)
    if type(attachment_only) is not bool: raise ValueError('附件导入模式无效')
    key='zhuazhua/raw/'+digest[:2]+'/'+digest
    cos=client(); bucket=os.environ['CAPTURE_COS_BUCKET']
    with connect() as db, db.cursor() as c:
        # A retry cannot create a second row; stale metadata cannot replace newer edits.
        c.execute('SELECT pg_advisory_xact_lock(%s)',(int(digest[:15],16),))
        c.execute('SELECT metadata,thumbnail_key FROM zhuazhua_captures WHERE digest=%s',(digest,))
        old=c.fetchone()
        if old is None:
            cos.put_object(Bucket=bucket,Key=key,Body=raw,ContentType=mime,ACL='private',Metadata={'sha256':digest})
            head=cos.head_object(Bucket=bucket,Key=key)
            if int(head.get('Content-Length',head.get('content-length',-1))) != len(raw): raise RuntimeError('COS size verification failed')
            c.execute('INSERT INTO zhuazhua_captures(digest,object_key,mime,size,width,height,metadata) VALUES(%s,%s,%s,%s,%s,%s,%s)',
                (digest,key,mime,len(raw),width,height,Json(meta)))
        elif not attachment_only and meta['modifiedAt'] >= old[0].get('modifiedAt',''):
            c.execute('UPDATE zhuazhua_captures SET metadata=%s,updated_at=now() WHERE digest=%s',(Json(meta),digest))
        if old is None or not old[1]:
            thumb=thumbnail(cos,bucket,digest,raw)
            c.execute('UPDATE zhuazhua_captures SET thumbnail_key=%s WHERE digest=%s',(thumb,digest))
    return {'ok':True,'digest':digest,'duplicate':old is not None,'url':'/vault/inbox/','storage':'cos'}

def listing(connect, query):
    q=query.get('q',[''])[0][:300].lower()
    offset=max(0,min(100000,int(query.get('offset',['0'])[0])))
    day=query.get('day',[''])[0]
    compact=query.get('summary',[''])[0]=='1'
    limit=max(1,min(60,int(query.get('limit',['24' if compact else '60'])[0])))
    if day and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day): raise ValueError('日期无效')
    with connect() as db, db.cursor() as c:
        metadata="jsonb_build_object('name',metadata->'name')" if compact else 'metadata'
        c.execute('''SELECT digest,'''+metadata+''',received_at::text,width,height,thumbnail_key FROM zhuazhua_captures
            WHERE (%s='' OR strpos(lower(metadata::text),%s)>0)
            AND (%s='' OR to_char((metadata->>'collectedAt')::timestamptz AT TIME ZONE 'Asia/Shanghai','YYYY-MM-DD')=%s)
            ORDER BY (metadata->>'collectedAt')::timestamptz DESC,digest LIMIT %s OFFSET %s''',(q,q,day,day,limit+1,offset))
        rows=c.fetchall()
    return {'items':[dict(digest=d,**m,receivedAt=t,width=w,height=h,imageURL=PREFIX+'image/'+d,thumbnailURL=(signed_image(key,int(time.time()//300)) if compact and key else PREFIX+'thumbnail/'+d)) for d,m,t,w,h,key in rows[:limit]],'more':len(rows)>limit}

def handle(handler, connect, method):
    path=urlsplit(handler.path).path
    if path!='/vault/inbox/' and not path.startswith(PREFIX): return False
    if handler.headers.get('Origin') not in (None,'https://qiuyiwu.com'):
        handler.reply(403,{'error':'来源不允许'}); return True
    is_device=device(handler)
    allowed=is_device or ((method=='GET' or handler.headers.get('Origin')=='https://qiuyiwu.com') and handler.authenticated())
    if not allowed:
        if path=='/vault/inbox/':
            handler.send_response(302); handler.send_header('Location','/admin/login.html?next=/vault/inbox/'); handler.send_header('Cache-Control','no-store');handler.end_headers()
        else: handler.reply(401,{'error':'请登录知行档案或连接爪爪设备'})
        return True
    try:
        if method=='POST' and path in (PREFIX+'notes',PREFIX+'events'):
            n=int(handler.headers.get('Content-Length','0'))
            limit=4096 if path.endswith('/events') else 2*1024*1024
            if not 0<n<=limit: raise ValueError('请求大小无效')
            data=json.loads(handler.rfile.read(n))
            if path.endswith('/events'): handler.reply(200,telemetry.record(connect,data))
            else: handler.reply(200,{'ok':True,'note':note_images(connect,notes.upsert(connect,data))})
        elif method=='GET' and path==PREFIX+'notes': handler.reply(200,notes.listing(connect,parse_qs(urlsplit(handler.path).query)))
        elif method=='GET' and re.fullmatch(PREFIX+r'notes/[0-9a-fA-F-]{36}',path):
            item=notes.detail(connect,path.rsplit('/',1)[-1])
            handler.reply(200 if item else 404,note_images(connect,item) if item else {'error':'笔记不存在'})
        elif method=='GET' and path==PREFIX+'metrics': handler.reply(200,telemetry.metrics(connect,parse_qs(urlsplit(handler.path).query)))
        elif method=='POST' and path==PREFIX+'captures':
            n=int(handler.headers.get('Content-Length','0'))
            if not 0<n<=90*1024*1024: raise ValueError('请求大小无效')
            handler.reply(200,upload(connect,json.loads(handler.rfile.read(n))))
        elif method=='GET' and path==PREFIX+'captures': handler.reply(200,listing(connect,parse_qs(urlsplit(handler.path).query)))
        elif method=='GET' and re.fullmatch(PREFIX+r'captures/[a-f0-9]{64}',path):
            item=detail(connect,path.rsplit('/',1)[-1])
            handler.reply(200 if item else 404,item or {'error':'图片不存在'})
        elif method=='GET' and re.fullmatch(PREFIX+r'(?:image|thumbnail)/[a-f0-9]{64}',path):
            digest=path.rsplit('/',1)[-1]
            with connect() as db, db.cursor() as c:
                c.execute('SELECT object_key,mime,thumbnail_key FROM zhuazhua_captures WHERE digest=%s',(digest,));row=c.fetchone()
            if not row: handler.reply(404,{'error':'图片不存在'})
            else:
                is_thumb='/thumbnail/' in path and row[2] is not None
                response=client().get_object(Bucket=os.environ['CAPTURE_COS_BUCKET'],Key=row[2] if is_thumb else row[0])
                body=response['Body'].get_raw_stream()
                try: handler.reply(200,body.read(),'image/jpeg' if is_thumb else row[1])
                finally: body.close()
        elif method=='GET' and path=='/vault/inbox/':
            handler.reply(200,(Path(__file__).parent/'web/capture-inbox.html').read_text(),'text/html; charset=utf-8')
        else: handler.reply(404,{'error':'接口不存在'})
    except notes.Conflict as e: handler.reply(409,{'error':'笔记已有更新，请保留本地草稿并重新载入','code':'version_conflict','current':e.current})
    except telemetry.RateLimited: handler.reply(429,{'error':'体验数据提交过于频繁'})
    except (ValueError,TypeError,KeyError) as e: handler.reply(400,{'error':str(e)})
    except Exception:
        # Never print cloud exception objects: they can contain signed request data.
        handler.reply(503,{'error':'保存服务暂时不可用，请保留当前内容并重试'})
    return True
