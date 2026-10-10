from pathlib import Path
import shutil,datetime,json,hashlib,subprocess
r=Path('/opt/agent-vault');b=Path('/var/backups/agent-vault')/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-standards');b.mkdir()
for rel in ['src/agent_vault/skill_registry.py','integrations/catalog.json','integrations/CHANGELOG.md']:
 dst=b/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(r/rel,dst)
p=r/'src/agent_vault/skill_registry.py';s=p.read_text();assert '# column-standards-v1' not in s
s=s.replace("or p.startswith('/vault/seminar/')", "or ('/vault/seminar/' in r['related_urls'] and p.startswith('/vault/seminar/'))")
s+='''
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
''';p.write_text(s)
c=r/'integrations/catalog.json';d=json.loads(c.read_text());d['version']='1.2.0';d['updated']='2026-10-11'
for ident,typ,rel in [('vault-column-standards','skill','skills/vault-column-standards/SKILL.md'),('vault-column-schema','reference','skills/vault-column-standards/references/columns.json')]:
 f=r/rel;dst=r/'integrations/releases/1.0.0'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
 d['entries']=[e for e in d['entries'] if e['id']!=ident];d['entries'].append(dict(id=ident,type=typ,version='1.0.0',path=rel,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
c.write_text(json.dumps(d,ensure_ascii=False,indent=2));p=r/'integrations/CHANGELOG.md';p.write_text(p.read_text()+'\n## 1.2.0 · 2026-10-11\n新增全栏目输入、总结与验收标准v1.0.0，可由MCP技能发现接口读取。是内容契约，不宣称已实现全栏目自动校验和写入。\n')
subprocess.run(['python3','-m','py_compile',str(r/'src/agent_vault/skill_registry.py')],check=True)
subprocess.run(['systemctl','restart','agent-vault'],check=True);print('BACKUP',b)
