"""Shared server-rendered channel navigation for live and generated documents."""
import re
from html import escape

ITEMS = [('全部内容','/vault/'),('阅读档案','/vault/reading/'),('视频频道','/vault/video/'),('深度读书','/vault/books/'),('建造者观察','/vault/digest/'),('思考与作品','/vault/html/'),('研讨沉淀','/vault/seminar/'),('爪爪收件箱','/vault/inbox/'),('数据洞察','/vault/analytics.html')]

def render_channel(content, path):
    if path in ('/vault/video/','/vault/video/index.html'):content=content.replace('视频档案','视频频道')
    # Rename collection landing pages only; preserve historical article wording.
    if path in ('/vault/books/','/vault/books/index.html','/vault/digest/','/vault/digest/index.html','/vault/html/','/vault/html/index.html'):
        for old,new in [('榨书档案','深度读书'),('建造者日报','建造者观察'),('HTML 部署目录','思考与作品'),('分析文稿','思考与作品')]:
            content=content.replace(old,new)
    work = (path.startswith('/vault/html/') or path.startswith('/vault/seminar/')) and path not in ('/vault/html/','/vault/html/index.html','/vault/seminar/','/vault/seminar/index.html')
    admin = path.startswith('/admin/vault')
    links = ''.join('<a href="%s"%s>%s</a>' % (url, ' aria-current="page"' if (path in ('/vault/','/vault/index.html') if url=='/vault/' else path.startswith(url)) else '', name) for name,url in ITEMS)
    nav = '<nav class="vault-nav" aria-label="知行档案导航"><div class="vn-inner"><a class="vn-brand" href="/vault/">知行档案<span>KNOWLEDGE & PRACTICE</span></a><div class="vn-links">'+links+'</div><div class="vn-aux"><a href="/">个人主页 ↗</a><a href="/admin/dashboard.html">个人工作台 ↗</a></div></div>'
    if admin:
        sections=[('应用首页','/admin/vault/app'),('内容管理','/admin/vault/'),('阅读与笔记','/admin/vault/read'),('数据洞察','/admin/vault/insights'),('每日简报','/admin/vault/brief'),('Agent 接入','/admin/vault/integrations')]
        app_links=''.join('<a href="%s"%s>%s</a>'%(u,' aria-current="page"' if path==u else '',n) for n,u in sections)
        nav='<nav class="vault-nav" aria-label="知行档案导航"><div class="vn-inner"><a class="vn-brand" href="/admin/vault/app">知行档案<span>阅读、思考与实践</span></a><div class="vn-links">'+app_links+'</div><div class="vn-aux"><a href="/vault/">查看公开频道 ↗</a><a href="/admin/dashboard.html">← 个人工作台</a></div></div>'
    nav += '</nav>'
    for name,url in ITEMS[1:-1]:
        if path.startswith(url) and path not in (url,url+'index.html'):
            title = re.search(r'<title[^>]*>(.*?)</title>',content,re.S|re.I)
            nav += '<div class="vault-crumb"><a href="/vault/">知行档案</a> / <a href="'+url+'">'+name+'</a> / <span>'+escape(re.sub('<[^>]+>','',title[1]) if title else '正文')+'</span></div>'
    if path.startswith('/vault/seminar/') and work:
        # Replace this known seminar template's duplicate personal-site header only.
        if re.search(r'<header\b[^>]*class=["\']top["\']',content):
            toolbar='<header class="seminar-toolbar"><div class="st-inner"><a href="/vault/seminar/">← 研讨沉淀</a><div class="st-tools"><a href="/vault/skills/seminar-settlement/">本篇 Skill</a><button id="reading" type="button" aria-pressed="false">专注阅读</button><button id="print" type="button">打印 / PDF</button></div></div><div class="progress" aria-hidden="true"><span id="progress"></span></div></header>'
            content=re.sub(r'<header\b[^>]*class=["\']top["\'][^>]*>.*?</header>',lambda m:toolbar,content,count=1,flags=re.S|re.I)
        content=content.replace('</head>','<link rel="alternate" type="text/markdown" title="研讨沉淀 Skill" href="/vault/skills/seminar-settlement/SKILL.md"></head>',1)
    content = re.sub(r'<nav\b[^>]*class=["\'](?:nav|vault-nav)["\'][^>]*>.*?</nav>', '', content, flags=re.S|re.I)
    if admin: content = re.sub(r'<header\b[^>]*>.*?</header>', '', content, count=1, flags=re.S|re.I)
    theme='<script src="/vault/theme.js?v=1"></script>'
    assets='<link rel="stylesheet" href="/vault/'+('work-shell.css?v=3' if work else 'channel.css?v=8')+'" data-vault-theme="1">'
    content = re.sub(r'<script[^>]*src=["\']/vault/channel\.js[^>]*>\s*</script>','',content)
    content = re.sub(r'<link[^>]*href=["\']/vault/channel\.css[^>]*>','',content)
    if '</head>' in content: content=content.replace('</head>',assets+theme+'</head>',1)
    else: content=content.replace('</style>','</style>'+assets,1)
    cls=('vault-work' if work else 'vault-channel')+(' vault-admin' if path=='/admin/vault/' else '')
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
    if not work:content=content.replace(assets,assets+'<style>body{background:var(--v-bg);color:var(--v-ink)}</style>',1)
    if path=='/admin/vault/': content=content.replace(nav,nav+'<div class="admin-heading"><h1>内容管理</h1><p>整理资料，留下可继续思考的起点。</p></div>',1)
    if path.startswith('/vault/') and path.endswith('.html') and not path.endswith('/index.html') and path!='/vault/analytics.html':
        content=content.replace('</body>','<script src="/vault/reader-link.js?v=7"></script></body>')
    return content
