"""Seminar article metadata and reusable editorial instructions."""
import hashlib, json, re
from datetime import date
from pathlib import Path
from html import escape

SKILL_ROOT = Path(__file__).parents[2] / 'skills' / 'seminar-settlement'

def skill():
    return {'name':'seminar-settlement','version':'1.1.0',
            'instructions':(SKILL_ROOT/'SKILL.md').read_text(),
            'workflow':(SKILL_ROOT/'references/workflow.md').read_text(),
            'write_tool':'vault_publish_seminar',
            'caution':'Instructions do not authorize publication. Only publish user-authorized public articles.'}

def validate(args):
    if not isinstance(args,dict) or set(args)-{'title','html','summary','date','tags','request_id'}:
        raise ValueError('Invalid seminar arguments')
    for key,limit in [('title',200),('html',4000000),('summary',2000),('date',10),('request_id',120)]:
        value=args.get(key,'' if key=='summary' else None)
        if not isinstance(value,str) or len(value)>limit or (key!='summary' and not value.strip()):
            raise ValueError('Invalid '+key)
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,120}',args['request_id']):raise ValueError('Invalid request_id')
    if '<html' not in args['html'].lower() or '</html>' not in args['html'].lower():
        raise ValueError('A complete standalone HTML document is required')
    if date.fromisoformat(args['date']).isoformat()!=args['date']:raise ValueError('Invalid date')
    tags=args.get('tags',[])
    if not isinstance(tags,list) or len(tags)>12 or any(not isinstance(t,str) or not 1<=len(t)<=50 for t in tags):
        raise ValueError('Invalid tags')
    return {**args,'summary':args.get('summary',''),'tags':list(dict.fromkeys(tags))}

def fingerprint(args):
    return hashlib.sha256(json.dumps(args,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def public_metadata(args):
    return {'content_type':'seminar_settlement','date':args['date'],'summary':args['summary'],'tags':args['tags']}

def embed_metadata(content,metadata):
    # JSON in a script tag remains data even when a title contains markup.
    metadata={k:metadata[k] for k in ('content_type','date','summary','tags') if k in metadata}
    data=json.dumps(metadata,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    tag='<script type="application/json" id="vault-seminar-metadata">'+data+'</script>'
    if '</head>' in content:return content.replace('</head>',tag+'</head>',1)
    return re.sub(r'(<html\b[^>]*>)',lambda m:m[0]+tag,content,count=1,flags=re.I)

def collection_page():
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>研讨沉淀 · 知行档案</title></head><body class="vault-home"><main><section class="channel-hero"><div><div class="eyebrow">SEMINAR / 研讨与后续思考</div><h1>讨论之后，<br>留下可以继续思考的文章。</h1><p>从真实问题出发，保留研讨中的判断与后续深化，<br>把方法、证据和适用边界一起沉淀。</p></div><div class="hero-total" id="total">—<span>篇研讨文章</span></div></section><p><a href="/vault/skills/seminar-settlement/">查看本栏目的 Skill →</a></p><section class="channel-toolbar"><input id="search" type="search" aria-label="搜索研讨文章" placeholder="搜索标题、摘要或主题…"></section><div class="channel-meta"><span id="count" role="status">正在加载…</span><span>按文稿日期 · 新到旧</span></div><section class="waterfall" id="cards" aria-label="研讨文章"></section><div class="empty-state" id="empty" hidden>暂时没有匹配的研讨文章。</div><footer class="channel-footer"><span>研讨内容 · 后续讨论 · 方法与验证</span><a href="/vault/">全部档案 ↗</a></footer></main><script>
let rows=[];const $=s=>document.querySelector(s);function node(t,text,cls){const n=document.createElement(t);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n}function draw(){const q=$('#search').value.toLowerCase().trim(),found=rows.filter(x=>[x.title,x.summary,...(x.tags||[])].join(' ').toLowerCase().includes(q));$('#count').textContent=found.length+' 篇研讨文章';$('#empty').hidden=!!found.length;$('#cards').replaceChildren(...found.map(x=>{const card=node('article',undefined,'vault-tile'),c=node('div',undefined,'tile-content'),top=node('div',undefined,'tile-top');top.append(node('span','研讨沉淀','tile-type'),node('time',x.date||'未注明日期'));const h=node('h2'),a=node('a',x.title);a.href=x.url;h.append(a);c.append(top,h);if(x.summary)c.append(node('p',x.summary,'tile-summary'));const tags=node('div',undefined,'tile-tags');for(const t of (x.tags||[]).slice(0,4))tags.append(node('span',t));c.append(tags);const b=node('div',undefined,'tile-bottom'),read=node('a','阅读并做笔记 ↗');read.href=x.reader_url;b.append(node('span','与 AI 协作整理'),read);card.append(c,b);return card}))}$('#search').oninput=draw;fetch('/vault/catalog.json').then(r=>{if(!r.ok)throw Error();return r.json()}).then(x=>{rows=x.filter(r=>r.collection==='seminar').sort((a,b)=>(b.date||'').localeCompare(a.date||'')||b.modified-a.modified);$('#total').replaceChildren(document.createTextNode(String(rows.length)),node('span','篇研讨文章'));draw()}).catch(()=>{$('#count').textContent='暂时无法加载，请刷新重试。'});
</script></body></html>'''
