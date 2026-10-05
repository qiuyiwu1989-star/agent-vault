# 网页划线与笔记 SDK：产品架构与开发计划

状态：规划稿，2026-10-05。此阶段不创建独立仓库、不部署本地原文批注原型。Vault 是首个接入方；只有在第二个模块完成接入后，再决定仓库发布方式。

## 1. 产品定义

读者在原页面选择正文，立即保存划线或附加私人笔记；刷新、回访后，高亮与笔记仍可找到。点击高亮可查看和编辑；文章正文变化时，系统尝试重新定位，并清楚显示无法定位的笔记。一个站点只需提供文档 ID、正文容器和登录适配器，即可嵌入相同体验。

首版对象：已登录的个人读者，单人私有批注。支持 HTML 正文、桌面鼠标选择与移动端系统选择。范围包含划线、评论、列表、跳转、高亮重定位、导出用户自己的笔记。暂不承诺多人共享、协作评论、PDF 坐标批注、跨域免登录、浏览器扩展、AI 自动生成批注。

界面：选中文字后出现轻量操作条；右侧为可收起的笔记抽屉。打开页面不强制弹窗；若未登录，第一次尝试保存时引导登录并返回原文。无需跳到第二个阅读页面。批注区域使用 Shadow DOM 或等效样式隔离，并给移动端留足点击范围。

## 2. 边界与架构

```text
站点页面（Vault / 其他模块）
  └─ 内容适配器：稳定文档 ID、正文容器、版本、用户会话
      └─ @qiuyiwu/annotation-sdk（浏览器包）
          ├─ 选区捕获、操作条、笔记抽屉、高亮渲染
          ├─ 定位器：引用文字 + 前后文 + 正文快照版本
          └─ 传输适配器：list/create/update/delete/export
              └─ 批注 API（认证、授权、并发版本、审计）
                  └─ annotations 数据表
```

SDK 不直接操作 Vault 数据库，不持有站点长期凭据，也不决定用户能否读取某篇文档。服务端按当前会话和模块授权；请求内的 userId 仅作显示信息，不作为授权依据。MCP 是单独的服务端适配层，默认只能读取用户显式允许分享的笔记。

初期优先同域部署，如 `qiuyiwu.com` 的各模块；跨域站点接入时再增加 OAuth/短期嵌入令牌与明确的 CORS 白名单，不把内部 API 的会话 cookie 任意开放给第三方域名。

## 3. 对外接入契约

建议采用语义版本化 npm 包，同时提供可固定版本的浏览器文件。一个页面实例只绑定一个正文根节点；多篇文章列表页不自动扫描全站。

```js
import { mountAnnotations } from '@qiuyiwu/annotation-sdk';
const app = await mountAnnotations({
  container: document.querySelector('article[data-document]'),
  document: { namespace: 'vault', id: 'book-123', revision: 'sha256:...' },
  api: { baseUrl: '/api/annotations/v1', credentials: 'same-origin' },
  loginUrl: '/admin/login.html',
  locale: 'zh-CN',
});
// 路由卸载时 app.destroy()
```

`namespace + document.id` 由宿主提供且不能随 URL 或标题变化；`revision` 标识当前正文快照。SDK 提供 `mount/destroy/refresh`、`onSaved/onError` 事件；接受可配置的主题变量。公开配置不得包含服务端密钥。宿主正文可在加载后渲染，但挂载时必须已经稳定；正文变化时调用 `refresh`。

API 最小集合：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/documents/{namespace}/{id}/annotations` | 返回当前用户有权看的批注及定位状态 |
| POST | `/documents/{namespace}/{id}/annotations` | 建立划线或笔记；服务端校验引用与正文版本 |
| PATCH | `/annotations/{id}` | 按 `version` 更新评论，冲突返回 409 |
| DELETE | `/annotations/{id}` | 可恢复删除，留审计记录；首版 UI 可暂缓 |
| GET | `/documents/{namespace}/{id}/export` | 导出当前用户自己的批注 |

服务端应统一返回 `id, namespace, documentId, ownerId, quote, prefix, suffix, start, end, contentRevision, comment, visibility, version, createdAt, updatedAt, anchorStatus`。`ownerId` 由服务端会话写入并用来过滤，客户端不得指定。所有接口均验证文档访问权；写入需要同源 Origin、CSRF 防护和速率限制。

## 4. 原文定位与数据可靠性

定位基于宿主指定的正文容器，不从导航、脚注、按钮或整个 `document.body` 计算偏移。先定义一套版本化的正文纯文本归一化规则，SDK 与服务端使用同一规则；偏移以 Unicode code point 计数，不能混用 JavaScript UTF-16 长度。保存 `quote + prefix/suffix + start/end + contentRevision`。

显示时依次尝试：同版本精确位置 → 新版唯一引用 → 前后文辅助匹配。多个候选仍无法确定时标记 `unresolved`，保留笔记及引用，不猜位置。重叠划线要能显示；不重写原正文 DOM。采用 CSS Highlight API 并准备兼容渲染路径。图片、表格、跨块选择和动态正文列入实测矩阵；不能可靠定位时给出可理解提示。

## 5. 现有 Vault 代码的迁移判断

2026-10-05 源码核对：`knowledge.py` 已有 PostgreSQL `knowledge_notes`、引用/前后文/哈希、版本冲突和重定位；`knowledge.html` 是独立阅读页。`reader-link.js` 的原文抽屉原型只在本地工作树，尚未上线。该原型使用 `doc.text.indexOf(quote)` 寻找首次匹配和全页文本遍历；它与现有 `extract()` 的正文定义不一定一致，也没有跨模块文档命名空间，因此不能直接当公共 SDK 发布。

更关键的是，现有 `knowledge_notes` 仅以 `doc_id` 关联，`notes()` 未按用户过滤。当前 Vault 是个人后台场景；扩展成公共插件前，必须新增 `namespace/owner_id/visibility` 等字段和行级授权，并给旧笔记建立可审计的归属迁移。不能先把旧 API 开给其他模块。现有进程级 CSRF token 与页面模板绑定；SDK 应通过宿主同源安全端点获取短期会话信息，严禁将长期令牌放进静态脚本。

迁移顺序：先保留旧阅读页可用；新服务以适配层读取 Vault 老数据，完成归属确认与回填后切换写入；小范围试用期间比较同一篇文档的笔记数及内容哈希；确认一致才停止旧写入口。文章正文和旧批注均需备份，并提供回退到旧阅读页的开关。

## 6. 开发顺序与验收

1. **冻结契约**：确定稳定 `namespace/documentId`、正文归一化版本、授权模型、API 错误码；用 Vault 一篇书、阅读文章、分析文稿分别验证正文容器。
2. **抽取浏览器核心**：从原型抽出选区、定位、高亮、抽屉，去掉 Vault URL 和 DOM 假设；完成挂载、卸载、重复挂载、异步正文变化处理。
3. **实现批注服务**：数据迁移、用户归属、授权、并发更新、删除恢复、审计、导出。先同域，复用主站会话。
4. **Vault 试点**：先少量页面灰度，旧阅读页保留；验证桌面、手机、暗色、无登录、长文、重复引用、正文改版、两处重叠划线、失败重试。
5. **第二模块试接**：由第二模块只写薄适配器，不改 SDK 核心。若必须改核心，记录通用契约变更和兼容版本。试接通过后再独立建仓、发布版本并写接入示例。

完成判据：用户在原文选中后可保存、回访可见、编辑冲突明确、正文变化不误高亮；其他用户不能读写私人笔记；第二模块通过公开接入契约完成安装，且不依赖 Vault 路径。自动测试覆盖定位/归一化、权限边界、并发与迁移；真实浏览器验收覆盖桌面和移动端。生产发布需有备份、可关闭开关和回退演练。

## 7. 后续独立仓库建议

第二模块验收后建立 `annotation-sdk` 独立项目仓。仓库包含 `packages/sdk`、`packages/ui`、`packages/server-contract`、`examples/vault`、`examples/generic-html`、`docs` 和测试。Vault 仓只保留接入适配器及部署配置。版本从 `0.x` 开始，接入契约稳定并完成两模块回归后再标 `1.0`。是否公开 GitHub、许可证及包名在建仓时决定；代码脱离真实内容、账号、数据库凭据后再公开。
