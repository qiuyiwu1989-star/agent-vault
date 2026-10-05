# 当前运行链路

实线代表已实现；虚线代表尚未接通。

```mermaid
flowchart TD
  User[用户] --> Admin[本地管理后台 :8766]
  Admin --> Draft[保存草稿与历史修订]
  Draft --> Publish[显式发布到本地]
  Snapshot[71 个历史成果快照] --> Reader[本地阅读库 :8765]
  Publish --> Reader
  Reader --> Search[统一搜索与分类阅读]
  History[历史版本] --> Draft
  OD[OpenDesign Docs] -. MCP 打开与编辑待接入 .-> Draft
  Agent[其他 Agent] -. 统一接入待完成 .-> Draft
  OC[OpenClaw 当前 Skills] --> Old[原归档与上传脚本]
  Old --> Online[qiuyiwu.com/vault]
  Publish -. 尚未同步 .-> Online
```

日常使用：选择或新建成果，编辑，保存草稿，发布到本地，刷新阅读库。恢复历史时先载入版本，保存为新草稿再发布。重启使用 start-vault.command。

当前数据与页面都是本机版，未迁移现网后台。后台使用同一 SQLite 文件内的 managed 表；早期 CLI 的 strict v1 表不自动进入阅读版，不应宣称所有 Agent 已统一接入。
