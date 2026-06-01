# Cursor 安装指南

## 1. 安装 Skill

```bash
git clone https://github.com/spikesubingrui-design/boss-greeting-rank.git
cd boss-greeting-rank
./install.sh cursor
```

安装位置：`~/.cursor/skills/boss-greeting-rank`。

## 2. 启用 MCP

在 Cursor 设置中添加 MCP 服务器 **user-boss-recommend**（或你本机配置的 `@reconcrap/boss-recommend-mcp`）。

确认工具可用：`prepare_boss_chat_run`、`start_boss_chat_run` 等。

## 3. 运行时版本

需要 **boss-recommend-mcp ≥ 2.0.57** 以持久化招呼原文。见 [runtime/README.md](../runtime/README.md)。

## 4. 使用

在 Agent 模式中说：「用 boss-greeting-rank 对 XX 岗位做招呼排名」。

Agent 会按 `SKILL.md` 访谈需求并驱动 MCP；完成后用本仓库 `scripts/` 解析 report。
