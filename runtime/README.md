# 运行时依赖（boss-recommend-mcp）

本 Skill **不包含** 浏览器自动化实现，依赖 npm 包：

```bash
npm install -g @reconcrap/boss-recommend-mcp@^2.0.57
```

## 2.0.57 新增（招呼原文）

- 点开候选人后抓取聊天首条消息
- 写入 `report.json` → `candidate.greeting_text`、`conversation_preview`
- 来源：`historyMsg` 网络包 / 聊天 DOM / 列表预览（降级）

### 检查版本

```bash
npm list -g @reconcrap/boss-recommend-mcp
```

### 手动补丁（仅当无法升级 npm 时）

将 `patches/2.0.57/` 内文件覆盖到全局包：

```bash
PKG="$(npm root -g)/@reconcrap/boss-recommend-mcp"
cp patches/2.0.57/conversation-greeting.js "$PKG/src/domains/chat/"
# detail.js / run-service.js 改动较大，建议直接升级 npm 或使用 diff
```

覆盖后重启 OpenClaw / Cursor MCP 进程。

## OpenClaw 说明

OpenClaw 通常已注册 `boss-recommend__*` 工具，**不必**在 Cursor 里再配一遍 MCP；但仍需保证后台 npm 包版本 ≥ 2.0.57。

## 许可

`@reconcrap/boss-recommend-mcp` 为独立项目，其许可与本仓库 MIT 无关。本仓库 `patches/` 仅作升级参考。
