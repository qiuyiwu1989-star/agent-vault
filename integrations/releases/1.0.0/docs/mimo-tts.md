# MiMo 简报播报 · 2026-10-09

每日简报“听简报”使用服务端 MiMo-V2.5-TTS，Token Plan CN OpenAI兼容 /v1/chat/completions，assistant消息携带待合成文本、mimo_default音色、WAV输出。不使用 /anthropic 接口。按300字分段，提供暂停/继续、停止；失败明确报错，不静默回退浏览器合成。

密钥位于服务器 /etc/agent-vault/mimo.env（root0600），systemd drop-in mimo.conf加载；不在代码、页面、日志。音频按内容SHA256缓存于 /var/lib/agent-vault/tts（agentvault0700，音频0600），仅已登录且CSRF通过的POST可请求；简报里的笔记文字随播报发往MiMo。当前按点击生成，不增加定时推送。

备份 /var/backups/agent-vault/20261009-113445-tts；回退恢复code.tar.gz及此前mimo.conf（首次则移除新增drop-in），daemon-reload并restart。保留数据库和缓存。23单测、JS语法、生产隔离回归通过，匿名TTS401；真实MiMo短句生成WAV成功。未完成整份简报及浏览器试听验收。
