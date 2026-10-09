"""Render versioned integration documentation without owning the integrations UI."""
import json,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'integrations'
def catalog():return json.loads((ROOT/'catalog.json').read_text())
def panel():
 c=catalog();parts=['<section id="vault-versioned-docs"><h2>Vault 技能与接口说明</h2><p>资料版本 '+html.escape(c['version'])+' · '+html.escape(c['updated'])+'</p><ul>']
 for e in c['entries']:parts.append('<li><a href="/api/inside/vault/knowledge/integration-doc?id='+html.escape(e['id'])+'">'+html.escape(e['id'])+'</a> · '+html.escape(e['type'])+' · v'+html.escape(e['version'])+'</li>')
 return ''.join(parts)+'</ul><p>版本来源：integrations/catalog.json；修订留档于 releases，变更记录随版本提交。</p></section>'
def document(ident):
 c=catalog();e=next((e for e in c['entries'] if e['id']==ident),None)
 if not e:raise ValueError('说明不存在')
 return (ROOT/'releases'/e['version']/e['path']).read_text()
