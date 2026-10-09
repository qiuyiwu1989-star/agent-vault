---
name: vault-daily-brief
description: 生成 Vault 私人内容日报讲稿及 MiMo 音频，汇总资料、阅读笔记和追问；用于按日期生成或重生成简报，不自动发布或设定推送。
metadata:
  version: 1.0.0
---

# Vault 日报生成

以指定日期（默认 Asia/Singapore 当天）为准。确认服务器当前 Vault 实例；不要从其他项目复制密钥。

1. 用 Knowledge.brief(day) 取已归档资料和笔记，保留 sources、日期、原文链接及生成方法。当天没有资料时明确写“近期回顾”，不能把旧资料描述为当天新闻。
2. 核对讲稿中的引用与判断。当前规则摘编不是经过模型核验的研究结论；跨文章共现只用于提出问题。旧笔记表与新批注 SDK 的覆盖范围需要另行核实，不能声称包含所有划线。
3. 使用 scripts/generate.py，在既有 agent-vault 服务账号环境运行；需要 MIMO_API_KEY、MIMO_BASE_URL 和可写 VAULT_TTS_CACHE。密钥不作为命令行参数，不写入产出。
4. MiMo 请求使用 assistant 消息、mimo-v2.5-tts、mimo_default、WAV。长讲稿按300字分段，复用内容缓存，合并前验证采样率、位宽、声道一致。失败保留已缓存片段；不要静默改用浏览器语音。
5. 核对讲稿、原文引用、完整WAV可解码与时长；试听与技术检查分别报告。输出保存在私有目录，仅登录后可访问；不会自动创建公开链接或定时任务。

实现参考：../../docs/mimo-tts.md、../../docs/reading-intelligence.md。每次流程/API变更同次更新技能版本、integrations/catalog.json 和 CHANGELOG.md。
