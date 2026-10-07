# 后台应用中心 · 2026-10-07

入口 `/admin/dashboard.html`。16张应用卡片集中展示，按内容创作、知识资产、信息输入、网站管理筛选并支持文字搜索。Vault独立应用内部保留笔记、洞察、简报等功能。合并重复PPT链接；既有15个不同应用URL全部保留，资产统计和活动API脚本保留。

部署采用现有受认证nginx精确location，alias `/opt/agent-vault/deploy/app-center.html`。保留原主站Git管理的 `/var/www/html/admin/dashboard.html`，避免全站发布覆盖服务器已有的其他应用进展。本文件目前是后台首页的生效来源，更新应用列表应修改本模板；后续应将该来源并入主站统一应用注册表。

备份 `/var/backups/agent-vault/20261007-134537-app-center`。nginx -t及reload成功，模板SHA256 24492650fe0dd04d90fce6f27b1f583c32755d2db7bc10714f3fe66f2ec1f4d3。所有旧应用URL保留检查和内联JS语法检查通过，生产匿名请求仍跳登录。浏览器工具超时，登录后视觉、搜索筛选点击未验收。回滚恢复备份nginx.conf至Vault片段，nginx -t再reload，即恢复主站原首页。
