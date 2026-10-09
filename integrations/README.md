# Vault Skill / MCP 版本资料

后台入口 `/admin/vault/integrations`；现有页面由另一位 Agent 开发，版本资料作为服务端附加区域，不覆盖其页面。catalog.json列出版本、来源和SHA256；releases目录保留每版正文，CHANGELOG记录修订。无凭据与私人内容。

以后修改技能、MCP契约或日报生成流程时，同次提交更新catalog、版本快照和CHANGELOG；不能只改网页文案。新版本通过范围部署合入，先比对生产代码，防止覆盖并行Agent。当前公开skill_registry是另一条发现入口，本次未擅自将后台运维说明公开。
