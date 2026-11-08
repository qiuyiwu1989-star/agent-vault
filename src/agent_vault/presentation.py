"""Verified presentation repairs, leaving archived source and revisions untouched."""
import re
from html import unescape

def repair_presentation(content,path):
    if path=='/vault/digest/2026-09-30-ai-builders-digest.html':
        # A prior formatter embedded a full anchor into href. Recover only its actual URL.
        content=re.sub(r'<a href="<a class="ref" href="(https?://[^"<>]+)" target="_blank" rel="noopener">阅读原文</a>" target="_blank" rel="noopener">([^<>]+)</a>',lambda m:'<a href="'+m[1]+'" target="_blank" rel="noopener noreferrer">'+m[2]+'</a>',content)
    css=''
    if path=='/vault/analytics.html':
        content=content.replace('阅读数据看板','归档数据看板').replace('数据源 vault-staging','公开归档快照 · 非阅读行为统计')
        css='.trust.t2{color:#775100}'
    if 'ceo-os-panorama-v0.' in path:
        css='.arch{min-width:0;max-width:100%;box-sizing:border-box}.wrap,.hero,.grid,.cols{min-width:0} @media(max-width:700px){.hero,.grid,.cols{grid-template-columns:minmax(0,1fr)} .arch{padding-inline:8px}}'
    if 'ceo-os-workbench-v1/' in path:
        css='@media(max-width:700px){.top{flex-wrap:wrap;padding:0 14px}.top nav{max-width:100%;overflow-x:auto;flex-wrap:wrap}.top .brand{border:0}.stage>*{min-width:0}.cons{grid-template-columns:1fr}.crow{flex-wrap:wrap}.crow .tip{text-align:left}.left,.right{padding:20px 16px}}'
    if 'doc-13d1e8f7-773b-4bd4-bedf-a3bdf76d3312.html' in path:
        css='.experiment>*{min-width:0}.arena{grid-template-columns:repeat(6,minmax(0,1fr))}.agent{min-width:0} @media(max-width:700px){.experiment{grid-template-columns:minmax(0,1fr)}.arena{grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.stage,.controls{padding:14px}.agent{font-size:14px}.agent span{font-size:10px}}'
    if 'cordis-paper-deep-dive/' in path:
        css='.proof>*{min-width:0}'
    if 'education-narrative/' in path:
        css='@media(max-width:700px){.ring{display:flex;flex-direction:column;gap:12px;aspect-ratio:auto;margin-top:24px}.ring>svg{display:none}.ring .node,.ring .core{position:relative;left:auto;top:auto;transform:none;width:100%;max-width:100%;box-sizing:border-box}.ring .core{order:-1}.ring .seal{animation:none;transform:none;position:static;width:72px;height:72px;margin-left:auto}.ring .seal svg{width:72px;height:72px}}'
    if css:content=content.replace('</head>','<style data-vault-repair>'+css+'</style></head>',1)
    return content

def validate_public_html(content):
    """Reject a known corruption class before a new publication is written."""
    if re.search(r'''\bhref\s*=\s*["']\s*<a\b''',content,re.I):
        raise ValueError('链接属性中混入了HTML标签，请修复href后再发布；草稿仍保留。')
