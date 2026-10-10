"""Apply narrowly to the live source, preserving concurrent channel changes."""
from pathlib import Path
import datetime,shutil,subprocess
root=Path('/opt/agent-vault')
files=['src/agent_vault/channel.py','src/agent_vault/production.py','src/agent_vault/knowledge.py','src/agent_vault/web/channel.html']
backup=Path('/var/backups/agent-vault')/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-video-channel');backup.mkdir()
for rel in files:
 p=root/rel;dst=backup/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
nginx=Path('/etc/nginx/snippets/qiuyiwu-vault.conf');shutil.copy2(nginx,backup/'nginx.conf')
p=root/files[0];s=p.read_text()
if "('视频频道','/vault/video/')" not in s:s=s.replace("('阅读档案','/vault/reading/'),","('阅读档案','/vault/reading/'),('视频频道','/vault/video/'),",1)
s=s.replace('for name,url in ITEMS[1:6]:','for name,url in ITEMS[1:-1]:')
s=s.replace('    # Rename collection',"    if path in ('/vault/video/','/vault/video/index.html'):content=content.replace('视频档案','视频频道')\n    # Rename collection",1);p.write_text(s)
for rel in files[1:3]:
 p=root/rel;s=p.read_text().replace('books|reading|digest|html|seminar)', 'books|reading|digest|html|seminar|video)').replace("('books','reading','digest','html','seminar')","('books','reading','digest','html','seminar','video')");p.write_text(s)
p=root/files[3];s=p.read_text()
if "video:" not in s:s=s.replace("const names={","const names={video:'视频频道',",1)
s=s.replace("video:'视频档案'","video:'视频频道'");p.write_text(s)
s=nginx.read_text().replace('books|reading|digest|html|seminar)', 'books|reading|digest|html|seminar|video)');nginx.write_text(s)
try:
 subprocess.run(['python3','-m','py_compile',str(root/files[0]),str(root/files[1]),str(root/files[2])],check=True)
 subprocess.run(['nginx','-t'],capture_output=True,check=True)
 subprocess.run(['systemctl','restart','agent-vault'],check=True)
 subprocess.run(['systemctl','reload','nginx'],check=True)
except Exception:
 for rel in files:shutil.copy2(backup/rel,root/rel)
 shutil.copy2(backup/'nginx.conf',nginx);subprocess.run(['systemctl','restart','agent-vault']);raise
print('BACKUP',backup)
