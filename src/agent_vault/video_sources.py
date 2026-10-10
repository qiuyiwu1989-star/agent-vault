"""Video provenance from explicit metadata or original-source blocks only."""
import html,json,re
from pathlib import Path
from urllib.parse import urlsplit,unquote
LABELS={'douyin':'抖音','weixin_channels':'视频号','bilibili':'B站','youtube':'YouTube','other':'其他','unknown':'未标注'}
def platform(url):
    host=(urlsplit(url).hostname or '').lower()
    for domain,key in [('douyin.com','douyin'),('channels.weixin.qq.com','weixin_channels'),('bilibili.com','bilibili'),('b23.tv','bilibili'),('youtube.com','youtube'),('youtu.be','youtube')]:
        if host==domain or host.endswith('.'+domain):return key
    return 'other' if host else 'unknown'
def source(text):
    m=re.search(r'<script\b[^>]*id=["\']vault-video-metadata["\'][^>]*>(.*?)</script>',text,re.S|re.I)
    if m:
        try:
            d=json.loads(m[1]);key=d.get('source_platform','unknown')
            if key not in LABELS:key='unknown'
            return {'source_platform':key,'source_url':d.get('source_url',''),'source_account':d.get('source_account','')}
        except (ValueError,TypeError,AttributeError):pass
    block=re.search(r'<div\b[^>]*class=["\']src["\'][^>]*>(.*?)</div>',text,re.S|re.I)
    urls=re.findall(r'href=["\'](https?://[^"\']+)',block[1]) if block and '原视频' in block[1] else []
    url=html.unescape(urls[0]) if len(urls)==1 else ''
    return {'source_platform':platform(url),'source_url':url,'source_account':''}
def decorate(text,path,root):
    if path not in ('/vault/video/','/vault/video/index.html'):return text
    def card(m):
        opening,href,body=m.group(1,2,3)
        p=(Path(root)/'video'/unquote(urlsplit(href).path)).resolve()
        # absolute Vault URLs are allowed only within this collection
        if href.startswith('/vault/video/'):p=(Path(root)/unquote(urlsplit(href).path[len('/vault/'):])).resolve()
        key='unknown'
        if (Path(root)/'video').resolve() in p.parents and p.suffix=='.html' and p.is_file():key=source(p.read_text())['source_platform']
        return opening[:-1]+' data-source="'+key+'"><span class="video-source">'+LABELS[key]+'</span>'+body+'</a>'
    text=re.sub(r'(<a\b[^>]*class="card"[^>]*href="([^"]+)"[^>]*>)(.*?)</a>',card,text,flags=re.S)
    filters='<section id="video-source-filters" aria-label="按视频来源筛选">'+''.join('<button type="button" data-source-filter="'+k+'" aria-pressed="'+str(k=='all').lower()+'">'+v+'</button>' for k,v in [('all','全部'),*LABELS.items()])+'</section><p id="video-source-count" role="status"></p>'
    text=text.replace('<div class="grid">',filters+'<div class="grid">',1)
    assets='''<style>#video-source-filters{display:flex;gap:8px;flex-wrap:wrap;margin:24px 0 12px}#video-source-filters button{padding:8px 16px;border:1px solid var(--v-line);border-radius:24px;background:var(--v-bg);color:var(--v-ink);cursor:pointer}#video-source-filters button[aria-pressed=true]{background:var(--v-accent);color:white}.video-source{display:inline-block;font-size:12px;color:var(--v-accent);margin-bottom:10px}.card[hidden]{display:none!important}</style><script>(()=>{const cards=[...document.querySelectorAll('.card[data-source]')];function apply(key){let n=0;cards.forEach(c=>{c.hidden=key!=='all'&&c.dataset.source!==key;if(!c.hidden)n++});document.querySelector('#video-source-count').textContent=n?'共 '+n+' 条视频':'这个来源暂时没有视频';document.querySelectorAll('[data-source-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.sourceFilter===key)))}document.querySelectorAll('[data-source-filter]').forEach(b=>b.onclick=()=>apply(b.dataset.sourceFilter));apply('all')})();</script>'''
    return text.replace('</body>',assets+'</body>')
