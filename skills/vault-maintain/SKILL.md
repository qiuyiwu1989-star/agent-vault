---
name: vault-maintain
description: "Maintain a local Agent Vault: find, submit, revise, publish or roll back knowledge documents when the user requests these actions."
---

# Vault 维护

先读取仓库 `docs/contract-v1.md` 和 `README.md` 的接入约定。从当前环境确认仓库路径及权威 root，不从其他 Agent 的路径推断。

使用 `python3 -m agent_vault.cli`，在仓库根设置 `PYTHONPATH=src`；所有存储命令显式传 `--root`。CLI 帮助列出准确参数。

1. `list` 查找已有成果，必要时 `get ID` 读取来源和正文。相同来源换标题不自动成为新成果，先判断是修订还是新的分析。
2. `validate 文件 --collection 类型`；失败按错误修正，不绕过检查。
3. `submit 文件 --collection 类型 --actor 标识` 只生成草稿。修订必须提供 `--id`、`--expected` 和 `--reason`。
4. 遇到版本冲突重新 get 并比较，保留两方有意义的内容；无法合并时说明冲突。
5. 用户要求发布或实例已有明确自动发布规则时，才调用 `publish ID --revision N --actor 标识`。该版本只生成本地版本，不等于上线。
6. 核对返回目录的 catalog.json、页面、active 结果；回报 ID、revision、状态与实际预览路径。

回滚显式使用已有 release ID，保留历史。不要直接复制某个客户端目录覆盖正式索引，不手改 SQLite，不把 actor 当作认证凭据。
