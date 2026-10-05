# 批注 SDK 首版实施记录

2026-10-05：在 agent-vault 中新增 `sdk/annotation` 独立前端包（ESM，0.1.0，尚不发布 npm）、Vault 薄适配器和 `web_annotations` 服务。宿主提供稳定正文容器与文档 ID；SDK 管选区、抽屉、笔记列表、CSS 高亮和销毁。服务端通过主站的签名人类会话识别用户，按 owner/namespace/document 过滤；自动化 Bearer 不可冒充人类批注。写入校验 CSRF、内容哈希和精确引用，编辑使用版本冲突。原有知识笔记接口不开放给其他模块。

服务器安装前已查询现有 `knowledge_notes` 数量为 0。若以后非零，需要先对账、备份并按用户归属迁移；不能把无归属的旧记录公开给多用户。文章原文件保持不变，服务端向正文页注入 SDK 加载器。CSS Highlight 不支持时仍可在侧栏读笔记，页面内高亮会降级。

验证：本机 23 个 Vault 单元测试、3 个 SDK 锚点测试通过；隔离 PostgreSQL 的知识与生产回归通过，其中实际 HTTP 覆盖两名用户隔离、版本冲突与陈旧正文拒绝。浏览器真实选区、移动端与视觉仍需在生产上线后检查。部署前备份服务文件、nginx 片段和数据库；回退恢复服务和 nginx，并保留新表中的笔记，避免回滚时丢失用户数据。

## 生产试点结果

2026-10-05 已在 A 机部署 Vault 原文页插件。部署前 `knowledge_notes=0`；备份 `/var/backups/agent-vault/20261005-123234-annotation-sdk/` 包含原 sidecar、nginx 片段与 PostgreSQL dump，数据库包权限 600、目录 700。新表 `web_annotations` 初始化成功，当前真实记录 0。正式 HTTPS 四个 SDK JS 资源 200 且 MIME 正确，文章返回 v7 加载器；新批注 session 与文档 API 未登录返回 401。隔离 PostgreSQL 业务回归（含两用户隔离、冲突、过期原文拒绝）通过，`sudo nginx -t` 通过，服务 active。

真实已登录浏览器的选择、保存与重新打开尚未验收：本轮浏览器工具导航超时。原文页遇到初始化错误时提供旧阅读页入口；服务端无法读取其他用户私人批注。移动端触摸选择与点击已有高亮的交互已实现，但也需实际设备复核。
