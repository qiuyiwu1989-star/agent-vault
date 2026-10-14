# 历史原型说明（归档）

以下为2026-10-14整理前的README，仅用于解释早期本地原型，不代表当前生产能力。

> 阅读笔记、跨文章洞察、简报与只读 MCP 已于 2026-10-05 上线，见 [本轮交付与使用说明](docs/reading-intelligence.md)。

> 2026-10-05：生产管理已部署，入口 https://qiuyiwu.com/admin/vault/ 。当前部署、验证边界和回退说明见 [生产运行记录](docs/production.md)。以下本地原型说明不代表生产配置。

# Agent Vault

Agent 中立的知识成果归档核心。维护同一权威内容库，生成给人阅读的静态 HTML 与给 Agent 使用的 JSON 目录。OpenClaw、Codex 等通过相同 CLI 提交文稿。

**当前版本：本地原型 0.1。没有接管 qiuyiwu.com，没有远程 API、鉴权或常驻服务。** 所有 `publish` 操作只创建本地静态发布版本。个人内容、凭据与第三方原始技能包不进入此仓库。

## 快速运行

需要 Python 3.10+，运行核心不依赖第三方库。仓库根目录执行：

```bash
export PYTHONPATH="$PWD/src"
python3 -m agent_vault.cli validate examples/2026-10-04-reading-example.md --collection reading
python3 -m agent_vault.cli --root .vault submit examples/2026-10-04-reading-example.md --collection reading --actor local-demo
python3 -m agent_vault.cli --root .vault list
```

用提交返回的真实 ID 发布到本地（替换 `<ID>`）：

```bash
python3 -m agent_vault.cli --root .vault publish '<ID>' --revision 1 --actor local-demo
python3 -m agent_vault.cli --root .vault active
```

打开返回目录中的 `index.html` 预览。需要本地 HTTP 预览时，只服务返回的 release 目录，**不要服务 `.vault` 根目录**，该目录包含草稿与历史数据库。

也可在虚拟环境执行 `pip install -e .`，然后使用 `vault` 命令。无需设置服务器密码或安装 OpenClaw。

## 已实现

- 严格中文元数据契约、真实日期、文件名日期一致性、标签及摘要长度检查。
- SQLite 事务统一存储：不可变修订、预期版本冲突、同内容同路径幂等提交、操作日志。
- 集合身份独立保留：books / reading / digest / html。
- 草稿提交与本地发布分开；修订草稿不替换已发布正文。
- 完整发布快照：从已发布清单构建所有分类、首页和 catalog.json。
- 成功完成后才在数据库事务中切换 active_release；失败构建目录不会成为活动版本。
- 回滚发布快照，不删除后续草稿或历史修订。
- 同时输出稳定 ID 页面和原文件名页面，便于逐步迁移。

## 接入约定

所有客户端必须写入**同一台主机上的同一个 root**。不能让多台机器各建一个数据库再复制目录覆盖。SQLite 文件不支持通过网络共享目录作为远程协作协议；远程 API 是后续里程碑。

`--actor` 是审计标识，不是身份认证。CLI 当前仅面向可信本地执行环境；若给不受信客户端开放写入，必须先建设鉴权与权限层。

修订前用 `get <ID>` 获取当前版本，提交时提供 `--id <ID> --expected <revision> --reason '变更原因'`。不自动覆盖冲突。完全相同内容重试会返回 unchanged；跨文件名的相同来源目前不自动去重，生产 Skill 应先查询目录。

机器结果为 JSON；失败返回非零退出码。发布成功只代表本地版本构建完成，不代表已经上传、上线或完成内容事实核查。

## Agent Skills

- [通用维护](skills/vault-maintain/SKILL.md)：查找、提交、修订、发布核验、回滚。
- [阅读档案](skills/reading-archive/SKILL.md)：外部内容提炼，区分原文和 Agent 判断。
- [榨书](skills/book-press/SKILL.md)：六阶段阅读分析与来源边界。
- [建造者日报](skills/builders-digest/SKILL.md)：逐条来源、事件日期、业务相关性。

技能包应与仓库一起保留；各运行环境加载对应 SKILL.md。此版本未自动安装到任何 Agent 的全局技能目录。

## 验证

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 当前限制与后续

HTML 渲染仅实现安全的基础标题、段落和代码块，Markdown 表格、富文本链接等尚未完整渲染。`html` 集合当前仅支持 Markdown 成果，现存交互式 HTML/附件迁移未实现。历史格式已支持独立待审导入、字段证据和 HTML/资源原字节保全，尚未接入正式发布。远程 API、权限、全文搜索、定时调度、生产部署和浏览器视觉验收均未完成。

原始 HTML 不直接执行；成熟实现应单独定义可信交互成果及其展示隔离策略。

[输出契约](docs/contract-v1.md) · [迁移与里程碑](docs/migration.md)

开源发布前需确定许可证并核查第三方来源。当前未指定开源许可证，未创建远程 GitHub 仓库。

## 先用起来：本地阅读版

当前提供 71 个快照成果的统一搜索和分类入口，详情保留原已发布页面。运行 `./start-reader.command`，然后打开 http://127.0.0.1:8765/ 。关闭终端会停止服务；重新运行即可。启动文件针对当前本地快照，不是通用安装示例。

搜索覆盖快照页面文本，不含脚本/样式。阅读版使用 published HTML，不把 9/30 本地稿差异冒充已发布正文；迁移候选与原始副本仍分别保留。仅绑定本机地址，不上传内容；原页面可能加载原有外部字体或链接。

最小使用路径：先在本地查找阅读，新增内容暂由现有 OpenClaw 归档流程处理。该阅读版不会自动获取后续网站更新，新核心 CLI 的提交也尚未自动合并到阅读版。远程服务、迁移审核和正式切换后续迭代。

## 最小管理后台（已运行）

统一启动：`./start-vault.command`。阅读端 http://127.0.0.1:8765/ ，后台 http://127.0.0.1:8766/admin/ 。仅绑定本机；关闭启动终端后需重新启动，未安装开机自启服务。

后台支持查看历史成果、新建 Markdown/HTML、编辑标题摘要正文、保存草稿、显式发布到本地阅读库，以及载入历史内容为新草稿。后台和导入 HTML 的阅读端使用不同端口隔离，管理请求验证 Host、Origin 和会话令牌。这是单用户本地入口，不可直接暴露公网。

最小链路：后台 → managed_revisions → managed_published → 原始快照 + 已发布修改 → reader-site/catalog.json 与页面。源快照不回写。新建或修改页面尚使用基础 Markdown 渲染；复杂排版优先保留现有 HTML。历史候选、早期 strict CLI 与后台 managed 表尚未统一，不要混用为同一发布入口。后台本地构建尚非生产级原子发布；现网仍走原 OpenClaw 流程。

OpenDesign Docs 尚未配置或完成 MCP 打开/编辑/保存回写验证，不显示伪造的一键编辑功能。接入后应以 Vault 文档 ID 和 revision 关联外部文档，保存回 Vault 草稿后再发布。
