# Vault 频道统一设计 · 2026-10-05

以 reading 系列的暖纸色、砖红强调色、衬线标题为共同视觉。共享 channel.css/channel.js 负责频道导航及工作台子导航。首页 channel.html 使用真实 catalog 标题、摘要、日期、标签，支持分类、搜索和 CSS 多列卡片；移动端单列，支持系统深色模式。

原有静态栏目通过 nginx 响应注入 reader-link.js，再加载共同导航；未修改 OpenClaw 生成的文章文件。管理、阅读、洞察、简报由 production.py 注入共同样式。新归档自动进入动态首页。以后修改导航和视觉请修改共同资源，避免逐篇写入重复导航。

生产备份：`/var/backups/agent-vault/20261005-102707-channel/files.tar.gz`。恢复时只恢复 `/opt/agent-vault` 和 nginx 片段，执行 nginx -t 后重启服务及 reload；本次未迁移数据库或覆盖文章。

验证：23 个单元测试、隔离 PostgreSQL 的 knowledge_acceptance 和 production_acceptance 全通过；JavaScript 语法检查通过。正式 HTTPS 首页、四栏目、公开 BI、CSS/JS 均200且有预期模板/注入；catalog 返回真实摘要标签；私有 notes 与 MCP 未认证401。浏览器工具超时，真实桌面/手机视觉及交互未完成验收。

## 导航修正

2026-10-05：频道“个人工作台”统一进入 `/admin/dashboard.html`，Vault 属于个人后台的内容管理模块；后台工具网格增加 Vault 管理卡片，替代悬浮入口。各静态栏目直接加载带版本的共同导航脚本，不再依赖阅读按钮脚本间接加载；reader-link 路由支持查询版本。正式 HTTPS 四栏目已核实直接注入 v4，两个 JS 资源 MIME/200 正常。备份 `/var/backups/agent-vault/20261005-105939-navigation/`。实际浏览器视觉仍未验收。

## 服务端统一模板

2026-10-05：新增 channel.py，首页、四栏目、BI 和文章正文通过同一服务端模板输出导航，替换旧 nav；无需 JavaScript 即可看到完整导航。个人主页/个人工作台移到右侧辅助区，文章增加所属栏目面包屑。nginx 仅将限定 Vault HTML 路由交给 sidecar，其余附件保持静态服务；解析路径后检查位于 ROOT 内。原始内容文件与 OpenClaw 产出未改动。

备份 `/var/backups/agent-vault/20261005-115310-navigation/`。23项单测和隔离 production_acceptance 通过。正式 HTTPS 检查首页、四栏目、BI、日报正文：恰好一个共享导航，链接列表完全一致，无旧 nav，v5 CSS 已引用。未完成浏览器视觉验收。
