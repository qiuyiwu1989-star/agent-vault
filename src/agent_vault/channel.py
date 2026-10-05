"""Shared server-rendered channel navigation for live and generated documents."""
import re
from html import escape

ITEMS = [('全部内容','/vault/'),('阅读档案','/vault/reading/'),('榨书档案','/vault/books/'),('建造者日报','/vault/digest/'),('分析文稿','/vault/html/'),('数据洞察','/vault/analytics.html')]

def render_channel(content, path):
    admin = path.startswith('/admin/vault')
    links = ''.join('<a href="%s"%s>%s</a>' % (url, ' aria-current="page"' if (path in ('/vault/','/vault/index.html') if url=='/vault/' else path.startswith(url)) else '', name) for name,url in ITEMS)
    nav = '<nav class="vault-nav" aria-label="Vault 频道导航"><div class="vn-inner"><a class="vn-brand" href="/vault/">文档区<span>VAULT / QIU YIWU</span></a><div class="vn-links">'+links+'</div><div class="vn-aux"><a href="/">个人主页 ↗</a><a href="/admin/dashboard.html">个人工作台 ↗</a></div></div>'
    if admin:
        nav += '<div class="vn-work">'+''.join('<a href="%s"%s>%s</a>'%(u,' aria-current="page"' if path==u else '',n) for n,u in [('← 个人工作台','/admin/dashboard.html'),('Vault 内容管理','/admin/vault/'),('阅读与笔记','/admin/vault/read'),('跨文章洞察','/admin/vault/insights'),('每日简报','/admin/vault/brief')])+'</div>'
    nav += '</nav>'
    for name,url in ITEMS[1:5]:
        if path.startswith(url) and path not in (url,url+'index.html'):
            title = re.search(r'<title[^>]*>(.*?)</title>',content,re.S|re.I)
            nav += '<div class="vault-crumb"><a href="/vault/">文档区</a> / <a href="'+url+'">'+name+'</a> / <span>'+escape(re.sub('<[^>]+>','',title[1]) if title else '正文')+'</span></div>'
    content = re.sub(r'<nav\b[^>]*class=["\'](?:nav|vault-nav)["\'][^>]*>.*?</nav>', '', content, flags=re.S|re.I)
    if admin: content = re.sub(r'<header\b[^>]*>.*?</header>', '', content, count=1, flags=re.S|re.I)
    assets='<link rel="stylesheet" href="/vault/channel.css?v=5" data-vault-theme="1">'
    content = re.sub(r'<script[^>]*src=["\']/vault/channel\.js[^>]*>\s*</script>','',content)
    content = re.sub(r'<link[^>]*href=["\']/vault/channel\.css[^>]*>','',content)
    if '</head>' in content: content=content.replace('</head>',assets+'</head>',1)
    else: content=content.replace('</style>','</style>'+assets,1)
    cls='vault-channel'+(' vault-admin' if path=='/admin/vault/' else '')
    if re.search(r'<body\b',content,re.I):
        content=re.sub(r'<body([^>]*)>',lambda m:'<body'+m[1]+'>'+nav,content,count=1,flags=re.I)
        def body_class(m):
            attrs=m[1]
            if re.search(r'class=["\']',attrs):
                attrs=re.sub(r'(class=["\'])',lambda x:x[1]+cls+' ',attrs,count=1)
            else:attrs+=' class="'+cls+'"'
            return '<body'+attrs+'>'
        content=re.sub(r'<body([^>]*)>',body_class,content,count=1,flags=re.I)
    else:
        pos=content.index(assets)+len(assets)
        content=content[:pos]+'<body class="'+cls+'">'+nav+content[pos:]
    # Styling applies immediately, including historical bodies with existing classes.
    content=content.replace(assets,assets+'<style>body{background:var(--v-bg);color:var(--v-ink)}</style>',1)
    if path=='/admin/vault/': content=content.replace(nav,nav+'<div class="admin-heading"><h1>内容管理</h1><p>整理资料，留下可继续思考的起点。</p></div>',1)
    if path.startswith('/vault/') and path.endswith('.html') and not path.endswith('/index.html') and path!='/vault/analytics.html':
        content=content.replace('</body>','<script src="/vault/reader-link.js?v=5"></script></body>')
    return content
