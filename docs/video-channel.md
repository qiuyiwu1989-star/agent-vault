# 视频频道接入 · 2026-10-11

将现有 /vault/video/ 接入共同导航及首页分类“视频频道”，保留现有播放器、逐字稿及总结原文。首页仍全量聚合。扩展服务端HTML路由、知识语料集合与nginx范围以包含video；原附件继续静态服务。

当前线上代码含其他Agent变更，未以旧本地整文件覆盖；范围补丁在 deploy/patches/20261011-video-channel.py。备份 /var/backups/agent-vault/20261011-012906-video-channel。nginx -t及Python编译通过；HTTP检查首页、阅读页、视频页共用导航，catalog含视频条目，详情有共同导航。未完成浏览器播放器试听验收。

来源升级：视频列表增加来源标签和全部/抖音/视频号/B站/YouTube/其他/未标注筛选；catalog暴露source_platform/source_url/source_account。导入元数据为JSON脚本块，历史仅识别明确原视频区块。后台Skill/MCP区域新增video-archive与video-import-contract，资料目录1.1.0。备份20261011-013313-video-sources。来源规则检查、线上HTML标签与筛选、catalog及版本资料读取检查通过。未进行浏览器筛选点击验收。
