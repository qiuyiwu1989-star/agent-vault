"""Shared server-rendered channel navigation for live and generated documents."""
import re
import hashlib
from html import escape

ITEMS = [('全部内容','/vault/'),('阅读档案','/vault/reading/'),('视频频道','/vault/video/'),('深度读书','/vault/books/'),('建造者观察','/vault/digest/'),('思考与作品','/vault/html/'),('研讨沉淀','/vault/seminar/'),('爪爪收件箱','/vault/inbox/'),('标签索引','/vault/tags.html'),('数据洞察','/vault/analytics.html')]

def render_channel(content, path, archive_enabled=False):
    if path in ('/vault/video/','/vault/video/index.html'):content=content.replace('视频档案','视频频道')
    # Rename collection landing pages only; preserve historical article wording.
    if path in ('/vault/books/','/vault/books/index.html','/vault/digest/','/vault/digest/index.html','/vault/html/','/vault/html/index.html'):
        for old,new in [('榨书档案','深度读书'),('建造者日报','建造者观察'),('HTML 部署目录','思考与作品'),('分析文稿','思考与作品')]:
            content=content.replace(old,new)
    if 'id="vault-book-metadata"' in content:
        def shared_book_style(m):
            if hashlib.sha256(m[1].encode()).hexdigest()=='42fdbf7f0c0d870a9a83e4a1743e38c2a0741c2668e0345269146bc48df97941':
                return '<link rel="stylesheet" href="/vault/book-reader.css?v=1">'
            return m[0]
        content=re.sub(r'<style>(.*?)</style>',shared_book_style,content,count=1,flags=re.S)
    work = (path.startswith('/vault/html/') or path.startswith('/vault/seminar/')) and path not in ('/vault/html/','/vault/html/index.html','/vault/seminar/','/vault/seminar/index.html')
    admin = path.startswith('/admin/vault')
    admin = admin or path.startswith('/vault/inbox/')
    public_items=list(ITEMS)
    section=next(((n,u) for n,u in public_items[1:] if path.startswith(u) and path not in (u,u+'index.html')),None)
    if path.startswith('/vault/skills/') and path not in ('/vault/skills/','/vault/skills/index.html'):
        section=('Skill 库','/vault/skills/')
    detail=section is not None and not admin
    links=''.join('<a href="%s"%s>%s</a>'%(u,' aria-current="page"' if (path in ('/vault/','/vault/index.html') if u=='/vault/' else path.startswith(u)) else '',n) for n,u in public_items)
    browse='<details class="vn-browse"><summary>浏览栏目</summary><div class="vn-menu">'+links+'<a href="/vault/skills/">栏目 Skill</a><a href="/admin/dashboard.html">个人工作台 · 需登录</a></div></details>'
    brand='<a class="vn-brand" href="/vault/">知行档案</a>'
    aux='<div class="vn-aux"><a class="vn-workspace" href="/admin/dashboard.html" title="登录个人工作台">个人工作台 ↗</a></div>'
    if detail:
        nav='<nav class="vault-nav vn-detail" aria-label="知行档案导航"><div class="vn-inner">'+brand+'<a class="vn-parent" href="'+section[1]+'"><span aria-hidden="true">/</span> '+section[0]+'</a>'+browse+aux+'</div></nav>'
        # Detail navigation already provides the parent; remove only known duplicate book return.
        content=re.sub(r'<a[^>]*href=["\']/vault/books/["\'][^>]*>\s*←\s*深度读书\s*</a>','',content,count=1)
    else:
        nav='<nav class="vault-nav vn-index" aria-label="知行档案导航"><div class="vn-inner">'+brand+aux+'<div class="vn-links">'+links+'</div></div></nav>'
    if admin:
        sections=[('应用首页','/admin/vault/app'),('内容管理','/admin/vault/'),('阅读与笔记','/admin/vault/read'),('跨文章洞察','/admin/vault/insights'),('每日简报','/admin/vault/brief'),('收件箱','/vault/inbox/'),('Agent 接入','/admin/vault/integrations')]
        if archive_enabled: sections.insert(1, ('私人档案','/admin/vault/archive'))
        app_links=''.join('<a href="%s"%s>%s</a>'%(u,' aria-current="page"' if path==u else '',n) for n,u in sections)
        nav='<nav class="vault-nav vn-workspace-shell" aria-label="个人知行工作台"><div class="vn-inner"><a class="vn-brand" href="/admin/vault/app">知行档案</a><div class="vn-aux"><a href="/vault/">公开频道 ↗</a><a href="/admin/dashboard.html">个人工作台</a></div><div class="vn-links">'+app_links+'</div></div></nav>'
    if path.startswith('/vault/seminar/') and work:
        # Replace this known seminar template's duplicate personal-site header only.
        if re.search(r'<header\b[^>]*class=["\']top["\']',content):
            toolbar='<header class="seminar-toolbar"><div class="st-inner"><a href="/vault/seminar/">← 研讨沉淀</a><div class="st-tools"><a href="/vault/skills/seminar-settlement/">本篇 Skill</a><button id="reading" type="button" aria-pressed="false">专注阅读</button><button id="print" type="button">打印 / PDF</button></div></div><div class="progress" aria-hidden="true"><span id="progress"></span></div></header>'
            content=re.sub(r'<header\b[^>]*class=["\']top["\'][^>]*>.*?</header>',lambda m:toolbar,content,count=1,flags=re.S|re.I)
        content=content.replace('</head>','<link rel="alternate" type="text/markdown" title="研讨沉淀 Skill" href="/vault/skills/seminar-settlement/SKILL.md"></head>',1)
    content = re.sub(r'<nav\b[^>]*class=["\'](?:nav|vault-nav)["\'][^>]*>.*?</nav>', '', content, flags=re.S|re.I)
    if admin and not path.startswith('/vault/inbox/') and path != '/admin/vault/archive': content = re.sub(r'<header\b[^>]*>.*?</header>', '', content, count=1, flags=re.S|re.I)
    theme='<script src="/vault/theme.js?v=1"></script>'
    system='<link rel="stylesheet" href="/vault/system.css?v=1"><script defer src="/vault/system.js?v=1"></script>'
    assets='<link rel="stylesheet" href="/vault/'+('work-shell.css?v=3' if work else 'channel.css?v=8')+'" data-vault-theme="1">'
    content = re.sub(r'<script[^>]*src=["\']/vault/channel\.js[^>]*>\s*</script>','',content)
    content = re.sub(r'<link[^>]*href=["\']/vault/channel\.css[^>]*>','',content)
    if '</head>' in content: content=content.replace('</head>',assets+theme+system+'</head>',1)
    else: content=content.replace('</style>','</style>'+assets+theme+system,1)
    cls=('vault-work' if work else 'vault-channel')+(' vault-admin' if path=='/admin/vault/' else '')+(' vault-workspace' if admin else '')+(' vault-detail' if detail else '')
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
    from .home_captures import decorate as decorate_home_captures
    return decorate_home_captures(content, path)
