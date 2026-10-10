---
name: video-archive
description: 将视频链接或已取得的视频文件归档到 Vault 视频频道，保存来源平台、账号、原始链接及媒体状态；适用于 OpenClaw 等 Agent 的视频导入。
metadata:
  version: 1.0.0
---

# 视频归档

归档集合为 video，正文页面位于 /vault/video/。先查已有原始链接，修订已有记录时保留历史，不能以本机部分内容重建整集合。

每篇 HTML 写入以下元数据块（JSON值须正确转义，字符 `<` 编码为 `\u003c`）：

```html
<script type="application/json" id="vault-video-metadata">
{"source_platform":"douyin","source_account":"作者账号名","source_url":"https://www.douyin.com/video/视频ID","content_type":"video","media_status":"link_only"}
</script>
```

source_platform 枚举：douyin 抖音、weixin_channels 视频号、bilibili B站、youtube、other、unknown。source_account是实际账号，不是平台名。source_url保留实际导入链接；媒体CDN地址不能替代原始来源。仅明确原始链接或可追溯的导入记录可确定平台；正文提到的平台、作者身份、mp.weixin.qq.com文章链接均不能证明视频来自视频号。无法确认用unknown，账号未知留空。

media_status：link_only只收藏链接；file_saved已保存可播放文件。不得把链接收藏写成视频已下载。只有已有授权且实际取得文件时才能写file_saved。详情提供原视频入口，转录与摘要注明生成方式，不把AI摘要当作原话。

入库后检查：视频详情、频道卡片来源、按平台筛选、Vault首页聚合及原始链接。现有历史页会从明确“原视频”区块回填平台，新的归档必须使用元数据块。后台版本资料 id=video-archive。MCP只读检索不等于写入权限；未实现的导入工具不得虚构调用，沿当前实例已授权的发布流程归档。
