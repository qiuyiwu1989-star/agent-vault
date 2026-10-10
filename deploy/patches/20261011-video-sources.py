from pathlib import Path
import datetime,shutil,subprocess,json,hashlib
r=Path('/opt/agent-vault');b=Path('/var/backups/agent-vault')/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-video-sources');b.mkdir()
for rel in ['src/agent_vault/production.py','integrations/catalog.json','integrations/CHANGELOG.md']:
 p=r/rel;dst=b/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
p=r/'src/agent_vault/production.py';s=p.read_text();s=s.replace('from .admin import ADMIN','from .admin import ADMIN\nfrom .video_sources import decorate as decorate_video, source as video_source',1)
s=s.replace('obj=render_channel(obj,urlsplit(self.path).path)','obj=render_channel(obj,urlsplit(self.path).path)\n            obj=decorate_video(obj,urlsplit(self.path).path,ROOT)',1)
needle="        info=metadata.get('/vault/'+rel,{})";assert needle in s;s=s.replace(needle,needle+"\n        provenance=video_source(t) if rel.startswith('video/') else {}",1)
s=s.replace('result.append(dict(date=info.get', 'result.append(dict(**provenance,date=info.get',1);p.write_text(s)
c=r/'integrations/catalog.json';data=json.loads(c.read_text());data['version']='1.1.0';data['updated']='2026-10-11'
for ident,kind,rel in [('video-archive','skill','skills/video-archive/SKILL.md'),('video-import-contract','reference','docs/video-import-contract.md')]:
 p=r/rel;dst=r/'integrations/releases/1.0.0'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
 data['entries']=[e for e in data['entries'] if e['id']!=ident];data['entries'].append(dict(id=ident,type=kind,version='1.0.0',path=rel,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
c.write_text(json.dumps(data,ensure_ascii=False,indent=2));p=r/'integrations/CHANGELOG.md';p.write_text(p.read_text()+'\n## 1.1.0 · 2026-10-11\n新增视频导入Skill与来源契约：抖音、视频号、B站等来源字段及筛选，未知来源不猜测。\n')
subprocess.run(['python3','-m','py_compile',str(r/'src/agent_vault/production.py'),str(r/'src/agent_vault/video_sources.py')],check=True)
subprocess.run(['systemctl','restart','agent-vault'],check=True);print('BACKUP',b)
