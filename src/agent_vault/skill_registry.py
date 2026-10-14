"""Discoverable, public editorial Skills; executable publishing remains separate."""
import hashlib
from html import escape
from .seminar import skill

BASE='/vault/skills/'
def listing():
    s=skill()
    return [dict(id=s['name'],name='研讨沉淀',version=s['version'],description='结合研讨转写与后续对话，形成文章、方法与适用边界。',url=BASE+s['name']+'/',source_url=BASE+s['name']+'/SKILL.md',related_urls=['/vault/seminar/'],write_tool=s['write_tool'],hash=hashlib.sha256(s['instructions'].encode()).hexdigest())]
def get(ident=None,url=None):
    rows=listing()
    if url:
        from urllib.parse import urlsplit
        u=urlsplit(url)
        if u.netloc and u.netloc!='qiuyiwu.com':raise ValueError('Unknown Skill link')
        p=u.path
        matches=[r for r in rows if p in r['related_urls']+[r['url'],r['source_url']] or ('/vault/seminar/' in r['related_urls'] and p.startswith('/vault/seminar/'))]
    else:matches=[r for r in rows if r['id']==ident]
    if len(matches)!=1:raise ValueError('Skill not found')
    return {**matches[0],**skill()}
def page(ident=None):
    rows=listing()
    if ident:
        r=get(ident)
        body='<h1>'+escape(r['name'])+'</h1><p>版本 '+escape(r['version'])+' · <a href="'+r['source_url']+'">读取 SKILL.md</a></p><p><a href="/vault/seminar/">进入研讨沉淀 →</a></p><details open><summary>整理方法</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+escape(r['instructions'])+'</pre></details><details><summary>工作流程与输出约定</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+escape(r['workflow'])+'</pre></details>'
    else:
        body='<h1>Skill 库</h1><p>让每个栏目背后的整理方法可以阅读，也可以交给 AI 调用。</p>'+''.join('<section><h2><a href="'+r['url']+'">'+escape(r['name'])+'</a></h2><p>'+escape(r['description'])+'</p><p>版本 '+r['version']+' · <a href="'+r['source_url']+'">SKILL.md</a></p></section>' for r in rows)
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Skill 库 · 知行档案</title></head><body><main style="max-width:900px;margin:40px auto;padding:0 24px"><p><a href="/vault/">知行档案</a> / <a href="/vault/skills/">Skill 库</a></p>'+body+'<p>AI 接入：通过 vault_list_skills 查看目录，通过 vault_get_skill 按 id 或栏目链接读取。获取方法不代表获得公开发布授权。</p></main></body></html>'

# column-standards-v1: retain all existing registry behavior.
_previous_listing = listing
_previous_get = get
def _column_standard():
    from pathlib import Path
    import json
    root=Path(__file__).resolve().parents[2]/'skills/vault-column-standards'
    instructions=(root/'SKILL.md').read_text()
    return dict(id='vault-column-standards',name='栏目输入与总结标准',version='1.0.0',description='六个内容栏目的输入、总结、验收与多Agent边界。',url=BASE+'vault-column-standards/',source_url=BASE+'vault-column-standards/SKILL.md',related_urls=[],write_tool=None,hash=hashlib.sha256(instructions.encode()).hexdigest(),instructions=instructions,workflow=(root/'references/columns.json').read_text())
def listing():
    return _previous_listing()+[{k:v for k,v in _column_standard().items() if k not in ('instructions','workflow')}]
def get(ident=None,url=None):
    from urllib.parse import urlsplit
    row=_column_standard()
    if ident==row['id'] or (url and urlsplit(url).netloc in ('','qiuyiwu.com') and urlsplit(url).path in (row['url'],row['source_url'])):return row
    return _previous_get(ident,url)
