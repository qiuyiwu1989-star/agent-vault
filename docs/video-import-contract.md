# 视频导入契约 v1.0.0

以 skills/video-archive/SKILL.md 为操作规范。必填 source_platform、source_account（可空）、source_url（无法取得可空）、content_type=video、media_status。HTML持久化使用 application/json#vault-video-metadata，目录和首页从同一来源规则读取。

MCP兼容边界：现有只读MCP用于查询资料，不新增或宣称具有视频上传、下载、发布能力。Agent获取此规范后应通过已有授权写入链路执行。平台归属与内容形式分开，视频保存在video集合；链接去重，原链接追溯，重复导入修订而非重复发表。

来源元数据升级与页面生成规则必须同次更新版本清单和历史快照；不能仅改展示标签。当前版本提供来源卡片与平台筛选，未知来源不猜测。
