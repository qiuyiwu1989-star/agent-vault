"""Opt-in aggregate UX counters. Never persist content, identity, IP or URLs."""
import threading
import time
from collections import deque
from datetime import datetime, timezone
EVENTS={'search_completed','inbox_list_loaded','note_opened','note_saved','note_save_failed','image_upload_completed','note_editor_opened','note_imported','note_sync_completed','note_sync_failed'}
SOURCES={'web','desktop'}
OUTCOMES={'success','failure','cancelled'}
ERRORS={'none','network','validation','conflict','unauthorized','unknown'}
_lock=threading.Lock()
_recent=deque()
class RateLimited(Exception): pass

def init(connect):
    with connect() as db, db.cursor() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS zhuazhua_experience_daily (
            day date NOT NULL,event text NOT NULL,source text NOT NULL,outcome text NOT NULL,error_code text NOT NULL,
            samples bigint NOT NULL DEFAULT 0,duration_ms bigint NOT NULL DEFAULT 0,item_count bigint NOT NULL DEFAULT 0,
            PRIMARY KEY(day,event,source,outcome,error_code))''')

def validate(data):
    if not isinstance(data,dict) or set(data)-{'event','source','outcome','durationMs','count','errorCode'}: raise ValueError('体验数据字段无效')
    for key,choices in [('event',EVENTS),('source',SOURCES),('outcome',OUTCOMES),('errorCode',ERRORS)]:
        value=data.get(key,'none' if key=='errorCode' else None)
        if not isinstance(value,str) or value not in choices: raise ValueError('体验数据类型无效')
    result=dict(data,errorCode=data.get('errorCode','none'))
    for key,maximum in [('durationMs',600000),('count',1000)]:
        value=data.get(key,0)
        if type(value) is not int or not 0<=value<=maximum: raise ValueError('体验数据数值无效')
        result[key]=value
    return result

def record(connect,data):
    item=validate(data)
    # One personal workspace: global cap avoids storing identifying rate-limit keys.
    with _lock:
        now=time.monotonic()
        while _recent and _recent[0]<now-60: _recent.popleft()
        if len(_recent)>=120: raise RateLimited()
        _recent.append(now)
    with connect() as db, db.cursor() as c:
        c.execute("DELETE FROM zhuazhua_experience_daily WHERE day < ((now() AT TIME ZONE 'UTC')::date - 29)")
        c.execute('''INSERT INTO zhuazhua_experience_daily(day,event,source,outcome,error_code,samples,duration_ms,item_count)
            VALUES(%s,%s,%s,%s,%s,1,%s,%s) ON CONFLICT(day,event,source,outcome,error_code)
            DO UPDATE SET samples=zhuazhua_experience_daily.samples+1,
            duration_ms=zhuazhua_experience_daily.duration_ms+EXCLUDED.duration_ms,
            item_count=zhuazhua_experience_daily.item_count+EXCLUDED.item_count''',
            (datetime.now(timezone.utc).date(),item['event'],item['source'],item['outcome'],item['errorCode'],item['durationMs'],item['count']))
    return {'ok':True}

def metrics(connect,query):
    days=int(query.get('days',['7'])[0])
    if days not in (7,30): raise ValueError('仅支持 7 或 30 天')
    with connect() as db, db.cursor() as c:
        c.execute("DELETE FROM zhuazhua_experience_daily WHERE day < ((now() AT TIME ZONE 'UTC')::date - 29)")
        c.execute('''SELECT day::text,event,source,outcome,error_code,samples,duration_ms,item_count
            FROM zhuazhua_experience_daily WHERE day >= (now() AT TIME ZONE 'UTC')::date - (%s - 1) ORDER BY day DESC,event''',(days,))
        rows=c.fetchall()
    return {'days':days,'items':[dict(zip(('day','event','source','outcome','errorCode','samples','durationMs','count'),r)) for r in rows]}
