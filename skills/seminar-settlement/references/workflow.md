# 工作记录与产品边界

## 人的使用流程

1. 导入研讨录音，转写服务产生有来源标识的转写。
2. 在该场研讨下与 AI 对话：理解内容，纠正身份或错字，追问原因，补充证据。
3. 请求整理文章：把研讨及后续讨论一起成文，保留补充与纠正。
4. 阅读成稿并修改。文章认可与方法验证是两件事。
5. 按要求公开到知行档案“研讨沉淀”，后续在后台保留版本。
6. 下一次实践提供证据，再更新方法状态或生成新的沉淀文章。

录音导入继续复用已有转写服务。当前 Vault 不增加音频转写或对话界面；本阶段复用外部 AI 聊天和独立稿件编辑。

## 内部 report.json 建议结构

```json
{
  "schema_version": "1.0",
  "content_type": "seminar_settlement",
  "seminar_id": "稳定来源标识",
  "seminar_date": "2026-10-09",
  "speaker_map": {"speaker_0": {"name": "邱懿武", "basis": "本场用户明确确认"}},
  "sources": [{"id": "transcript-1", "kind": "transcript", "location": "私有素材位置"}],
  "followup_sources": [{"id": "conversation-1", "kind": "human_ai_dialogue"}],
  "claims": [{"id": "claim-1", "origin": "ai_synthesis", "source_ids": ["transcript-1"], "status": "unverified"}],
  "methods": [{"id": "method-1", "problem": "", "operation": "", "conditions": "", "test": "", "status": "candidate"}],
  "article": {"title": "", "markdown_path": "", "html_path": "", "status": "draft"},
  "writeback": {"request_id": "", "payload_hash": "", "document_id": null, "public_url": null}
}
```

私有结构记录来源与变化，不作为公开工具参数。claim 状态可用 unverified / supported / revised / rejected，method 状态可用 candidate / tested / revised；不因文章发布自动升级状态。没有证据的字段可以空缺，不伪造时间戳或原话位置。

## 对外文章元数据

MCP 仅接受 title、html、summary、date、tags、request_id。标题与摘要适合读者浏览；date 是文稿日期，研讨日期在正文单独表达；tags 是主题。内部原文路径、身份确认证据和完整对话不发送。

## 验收

文章能独立阅读；保留后续讨论的实质贡献；用户身份确认和后续纠正已纳入；每个原话可回查；研究出处支持对应论述；没有虚构共识；候选方法不写成已验证规律；公开页没有私有材料；重复写回不会增加重复文章。


## 私有来源追加协议（1.1）

页面：`/admin/vault/seminar-sources?id=<document_id>`。研讨文章末尾在本人会话验证成功后显示入口。私有查看仅接受配置的本人账号，普通 Bearer 凭据不能代替本人会话。

Agent 从私有页面的“由 AI 继续追加保存”下载专用 MCP 配置。端点仍为 `https://qiuyiwu.com/api/vault-mcp`。专用凭据只允许追加来源，不允许读取私有资料或发布文章；原有公开只读／HTML 发布凭据不获得来源追加权限。凭据不要写入 report、脚本、原始对话或公开文章。

```json
{"document_id":"doc-seminar-...","source_id":"codex-thread-稳定会话编号","messages":[{"id":"稳定消息编号","role":"user","text":"原文","timestamp":"2026-10-13T08:00:00Z"}]}
```

每批 1–200 条，每条最多 100000 字符；将传输批次控制在 1 MB 内。来源和消息编号仅使用字母、数字、下划线、点、冒号和短横线。优先使用原会话消息 ID；没有时生成并持久保存稳定映射，不能每次导出重置随机编号。时间未知留空，不把保存时间伪作对话时间。

保存前把 document_id / source_id / 消息 ID 映射及覆盖范围写入本地 report。超时或结果不明时复用原批次重试；added=0 且 duplicates 等于本批消息数表示已存在，不是失败。同一 ID 内容不同则停止覆盖，检查来源映射；需要更正时追加新消息并说明关系。

验收包含：本人能读取、匿名和其他账号被拒、普通 MCP 凭据被拒、重复追加不增加数量、内容冲突不部分写入、公开文章和搜索不出现原文。记录最后已保存的消息编号和缺失范围。追加成功不意味着相关判断成立，也不意味着文章已经更新。

Codex 本地原会话可用本 skill 的 [export_codex_dialogue.py](https://qiuyiwu.com/vault/skills/seminar-settlement/scripts/export_codex_dialogue.py) 导出批次。它以原始追加日志行号产生稳定 message id，适用于同一未重写的 session 文件；日志被重写或换来源时应使用新的 source_id，不能复用旧映射。导出目录每次使用独立快照，避免混入旧批次。脚本只准备负载，不持有凭据、不自动发送。跨应用使用对应应用的真实导出，不能伪造统一格式的原文。
