"""Render versioned integration documentation without owning the integrations UI."""
import json,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'integrations'
def catalog():return json.loads((ROOT/'catalog.json').read_text())
def panel():
 c=catalog()
 labels={'vault-column-standards': '各栏目归档标准 · 从这里开始', 'vault-maintain': '维护与发布档案', 'vault-daily-brief': '生成每日简报', 'reading-archive': '导入阅读资料', 'book-press': '整理深度读书', 'builders-digest': '整理建造者观察', 'video-archive': '导入视频档案', 'vault-readonly-mcp': 'MCP 查询接口', 'contract-v1': '通用输入契约', 'production': '部署与运行', 'reading-intelligence': '阅读分析与证据', 'mimo-tts': '简报语音生成', 'annotation-sdk-implementation': '划线与笔记 SDK', 'video-import-contract': '视频来源与必填字段', 'vault-column-schema': '栏目字段定义'}
 parts=['<section id="vault-versioned-docs"><h2>技能与接口资料库</h2><p>先读栏目标准，再选择对应技能。配置连接请使用上方的复制按钮。</p><p>① 确定内容栏目 → ② 按标准准备材料 → ③ 接入 Agent 并校验结果</p><p>资料版本 '+html.escape(c['version'])+' · '+html.escape(c['updated'])+'</p>']
 for kind,title in [('skill','归档与创作技能'),('mcp','连接与接口'),('reference','字段、部署与参考说明')]:
  parts.append('<h3>'+title+'</h3><ul class="doc-grid">')
  for e in c['entries']:
   if e['type']!=kind:continue
   parts.append('<li><a href="/api/inside/vault/knowledge/integration-doc?id='+html.escape(e['id'])+'">'+html.escape(labels.get(e['id'],e['id']))+'</a><small>'+html.escape(e['id'])+' · v'+html.escape(e['version'])+'</small></li>')
  parts.append('</ul>')
 return ''.join(parts)+'<p>每份资料保留独立版本，更新记录与历史版本一并保存。</p></section>'

def document(ident):
 c=catalog();e=next((e for e in c['entries'] if e['id']==ident),None)
 if not e:raise ValueError('说明不存在')
 return (ROOT/'releases'/e['version']/e['path']).read_text()
