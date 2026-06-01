# Contributing

感谢关注 Boss Greeting Rank（招呼智排）。

## 开发

```bash
python3 -m py_compile scripts/*.py
node runtime/test-conversation-greeting.js
```

## Pull Request

1. 说明变更场景（OpenClaw / Cursor / 脚本）
2. 不提交密钥、`screening-config.json` 或含个人隐私的 report
3. 更新 `CHANGELOG.md`

## 运行时补丁

对 `boss-recommend-mcp` 的改动请优先向上游提交；本仓库 `runtime/patches/` 仅作版本对齐参考。
