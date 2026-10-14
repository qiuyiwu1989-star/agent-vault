# Agent Vault · 知行档案

面向个人和多个 Agent 的知识归档、阅读、研讨与私有采集模块。生产入口为 [知行档案](https://qiuyiwu.com/vault/)，管理入口为 [应用首页](https://qiuyiwu.com/admin/vault/app)。

**2026-10-14 状态**：已有生产服务，采用 Python sidecar + PostgreSQL + 已发布 HTML + 私有 COS。代码已从生产回收对齐；早期本地 SQLite CLI 仍保留，但不是生产写入接口。本仓库不包含真实文章库、私人笔记、原始研讨对话、图片、令牌或数据库备份。

## 文档入口

- [当前架构与功能清单](docs/architecture.md)
- [实际流程与优化顺序](docs/current-flow.md)
- [本次源码同步与验证记录](docs/sync-20261014.md)
- [栏目标准](skills/vault-column-standards/SKILL.md)
- [版本化接入资料](integrations/README.md)
- [生产运行说明](docs/production.md)（历史部署记录，路径以当前架构核实为准）

## 当前功能

| 范围 | 功能 |
|---|---|
| 公开知识 | 全部内容、阅读、视频、深度读书、建造者观察、思考与作品、研讨沉淀 |
| 阅读 | 原文阅读、来源标记、划线和评注 SDK |
| 管理 | 草稿、修订、显式发布、历史恢复、外部修改冲突检查 |
| 洞察 | 公开统计看板、后台实体与证据、跨文档资料包 |
| 简报 | 按需生成、浏览器朗读与 MiMo TTS；不等于已设每日自动推送 |
| Agent | 只读 MCP、限定新增 HTML/研讨发布、私有研讨原文追加独立权限 |
| 私有采集 | 图片/OCR收件箱、COS原图、Markdown笔记、乐观版本冲突控制 |
| 标准 | 栏目契约、技能版本、公开技能发现和后台接入资料 |

## 开发与验证

Python 3.10+。本地核心 CLI 可用 `pip install -e .`；生产依赖用 `pip install -e '.[production]'`。生产服务依赖宿主登录、PostgreSQL及环境配置，不能直接把开发服务暴露公网。

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[production]'
PYTHONPATH=src python -m unittest discover -s tests -v
```

PostgreSQL集成测试需要显式测试DSN，未配置会跳过。仓库同步不会自动部署。发布前必须对比当前线上文件，防止覆盖其他 Agent 的改动。

## 源码结构

`src/agent_vault` 为运行代码；`web` 为页面；`sdk/annotation` 为公共批注组件；`skills` 为当前技能；`integrations/releases` 为历史契约快照；`tests` 为测试；`deploy` 为部署说明与历史定向补丁。

当前为单人宿主网站集成，并非开箱即用的多租户产品。未指定开源许可证，先以私有仓库管理代码。旧原型说明见 [历史归档](docs/prototype-history.md)。
