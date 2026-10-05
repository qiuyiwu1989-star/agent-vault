# 迁移与实施记录

## 依据

用户提供的 2026-10-03 Vault 包（16 个普通文件）及 2026-10-04 reading-archive 包（4 个文件）。只做资料审阅，不执行其中部署、消息发送、记忆写入或定时任务指令。

现有代码存在：归档入口不强制校验；本地整个 staging 重建分类索引；主链未重建首页；digest 借用 reading 导航；标签解析读取类型；intake 抓取全文直接归档。旧格式与新格式、日报结构、BookPress 输出模板也有漂移。

## 已完成：0.1 本地核心

统一新内容解析、事务提交、版本冲突、完整发布快照、回滚、CLI、示例及四份可随仓库分发的 Skills。仅使用合成内容验证，未导入个人真实资料。

## 下一阶段：0.2 存量导入及展示

1. 获取权威 staging/服务器内容快照与资源清单（当前包没有实际全部文稿）。
2. 输出只读迁移清单：文件哈希、旧 URL、集合、元数据缺失、重复候选，不重写来源文件。
3. 旧格式通过单独兼容导入器生成候选记录；未知字段不猜补，阻止未经核验的公开发布。
4. 增加成熟 Markdown 展示与 HTML 成果/附件模型，验证表格、链接、移动端及交互页面。
5. 对账原始文件数、候选成果数、待处理数与旧链接覆盖率。数量相等不足以证明正文和附件完整。

## 0.3 多环境接入

在权威主机运行单一写入服务，CLI 与 HTTP 接口共享核心；服务端做身份认证、权限范围、幂等请求与修订冲突。OpenClaw 调度保留在适配层；网站域名、品牌、个人业务背景放入实例配置。内容生产、归档发布、飞书/消息同步各自报告结果。

现有 CRON 目录为空；prepare-digest.js、local-supplement.js 和完整部署配置未提供。不得据此宣称已复现日报流水线。

## 0.4 生产切换与 GitHub 发布

完成备份、影子构建、逐 URL 核验、回滚演练后切换现网。发布器需在服务器侧原子切换站点版本；本地 active_release 数据库指针不自动改变 nginx。GitHub 发布前确定仓库归属、名称、许可证，并审核上游技能及脚本的授权。此仓库不附带上游包、个人实例凭据或私有文稿。

## 接口验收场景

- 两个客户端提交同一新文件：只有一份成果。
- 两个客户端更新 revision 1：一方成功，另一方冲突。
- 新客户端仅提交一篇文稿：此前发布文章全部保留。
- 任意正文渲染失败：活动版本与发布清单保持原样。
- 撤回一次发布版本：目录恢复旧快照，草稿和历史仍可读取。
- 生产验收还需真实 OpenClaw 与另一 Agent 分别完成端到端流程；当前线程里的模拟客户端测试不替代它。

## 快照审阅工具

```bash
PYTHONPATH=src python3 -m agent_vault.migration /path/to/snapshot.tar.gz --out .vault/migration/review
```

工具不运行包内代码或 HTML。检查路径、大小上限、清单哈希、源文稿与服务器副本差异、新契约兼容性，以及 HTML src/link href 本地资源引用。扫描不涵盖 CSS url、动态 JavaScript、srcset，也不检查网络资源或凭据；不得把结果当成完整安全审计。

原始文件按 SHA-256 保存到隔离 blobs，preservation.json 保留路径映射；report.json 提供机器清单，index.html 是转义后的审阅列表。校验不符返回非零退出码，仍保留证据。此工具尚不将历史内容正式入库或发布。

## 历史兼容导入（审阅态）

```bash
PYTHONPATH=src python3 -m agent_vault.legacy --root .vault/legacy-review import .vault/migration/review --actor migration-owner
PYTHONPATH=src python3 -m agent_vault.legacy --root .vault/legacy-review preview <返回的snapshot> --out .vault/legacy-preview
```

导入前重新核验保全文件与原 inventory，不只依赖 report 的结论。源文稿和服务器副本分别按原始字节保存；HTML 与包内资源在 legacy_files/legacy_blobs 中保留完整路径与内容。相同快照重试不重复创建记录。操作脚本与 Skills 不进入内容库。

兼容解析生成独立的元数据候选和行号证据，不改正文：中文标签变体、代码块内书籍元信息、文件名日期可识别。类型不擅自转成标签，输入类型不冒充来源，研究团队不直接冒充作者；抽取不到标 missing，存在多个值标 conflicting。字段缺失是解析器结果，不代表原文中绝对不存在；下一轮审阅需核对未命中字段。

历史成果目前进入专用 legacy_documents 表，全部为 needs_review；与 strict v1 的 drafts/published 分离。现有主 CLI 的 list/get 不含历史待审记录；通过 preview/candidates.json 检索。尚未实现审核提升至正式发布模型。

预览是转义后的原始内容，能核对 HTML 源码但不会运行交互页面。附件已保全，不等于浏览器加载验证完成。正式 HTML 展示隔离、旧 URL 路由、跨成果链接和完整富文本渲染仍需后续实现。
