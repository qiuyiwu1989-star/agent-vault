"""Public reading views. Writing and credentials retain their existing guards."""
from html import escape
from urllib.parse import urlsplit
import sqlite3
from . import seminar_sources

SECTIONS = [('/vault/inbox/','爪爪图片与笔记'),('/vault/annotations/','阅读批注'),('/vault/dialogues/','研讨原始对话'),('/vault/briefs/','内容简报')]

def text(value):
    return escape(str(value or ''))

def block(title, body):
    return '<details><summary>'+text(title)+'</summary><div class="record">'+text(body)+'</div></details>'

def handle(h, connect):
    path=urlsplit(h.path).path
    if path=='/admin/vault/seminar-sources':
        h.send_response(302);h.send_header('Location','/vault/dialogues/');h.send_header('Cache-Control','no-store');h.end_headers();return True
    if path not in ('/vault/annotations/','/vault/dialogues/','/vault/briefs/'):
        return False
    body=''
    with connect() as db, db.cursor() as c:
        if path=='/vault/annotations/':
            c.execute('SELECT document_id,record FROM web_annotations WHERE deleted_at IS NULL ORDER BY created_at DESC')
            for doc,r in c.fetchall():
                body+=block('《'+doc+'》 · '+str(r.get('quote',''))[:60], '摘录：'+str(r.get('quote',''))+'\n\n批注：'+str(r.get('comment','')))
        elif path=='/vault/briefs/':
            c.execute('SELECT day::text,record FROM knowledge_briefs ORDER BY day DESC')
            for day,r in c.fetchall():body+=block(day+' · 内容回顾',r.get('script',''))
        else:
            p=seminar_sources.BASE/'dialogues.sqlite'
            if p.exists():
                conn=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True)
                try:
                    groups=conn.execute('SELECT document_id,count(*) FROM messages GROUP BY document_id').fetchall()
                    for doc,count in groups:
                        body+='<h2>研讨对话 · '+str(count)+' 条消息</h2><p><a href="/vault/seminar/'+text(doc)+'.html">阅读对应研讨文章 →</a></p>'
                        for seq,role,message in conn.execute('SELECT seq,role,text FROM messages WHERE document_id=? ORDER BY seq',(doc,)):
                            body+=block(str(seq)+' · '+('用户' if role=='user' else 'AI')+' · '+message.replace('\n',' ')[:65],message)
                finally:conn.close()
    title=dict(SECTIONS)[path]
    nav=' · '.join('<a href="'+u+'">'+label+'</a>' for u,label in SECTIONS)
    html='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'''+title+''' · 知行档案</title><style>
main{max-width:940px;margin:36px auto;padding:0 20px}h1{font-size:32px;line-height:1.3}main p{line-height:1.8}details{border-bottom:1px solid var(--v-line,#d9ded5);padding:16px 0}summary{cursor:pointer;line-height:1.7;overflow-wrap:anywhere}summary:focus-visible,a:focus-visible{outline:2px solid currentColor;outline-offset:4px}.record{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.9;padding:20px 0;max-width:75ch}a{color:inherit;text-underline-offset:4px}
</style></head><body><main><h1>'''+title+'</h1><p>'+nav+'</p><p>点击标题展开全文。研讨包含探索与建议，不代表所有观点已确认。</p>'+ (body or '<p>目前还没有内容。</p>')+'</main></body></html>'
    h.reply(200,html,'text/html; charset=utf-8')
    return True
