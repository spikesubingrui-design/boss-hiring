/**
 * Standalone smoke test for greeting parsing logic (no boss-recommend-mcp install required).
 * Full integration test: run in boss-recommend-mcp >= 2.0.57 package root.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const dir = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(dir, "patches/2.0.57/conversation-greeting.js"), "utf8");

assert.match(src, /export function parseChatMessagesFromHtml/);
assert.match(src, /export function buildConversationPreview/);
assert.match(src, /historyMsg/);

console.log("runtime/test-conversation-greeting: patch file structure ok");
