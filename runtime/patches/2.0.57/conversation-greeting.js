import { htmlToText, normalizeText } from "../../core/screening/index.js";

function isResumeRequestSentMessageText(text = "") {
  const normalized = normalizeText(text);
  return Boolean(
    normalized.includes("简历请求已发送")
    || normalized.includes("已发送简历")
    || normalized.includes("已求简历")
    || normalized.includes("已索要简历")
  );
}

function isResumeAttachmentMessageText(text = "") {
  const normalized = normalizeText(text);
  return Boolean(
    /点击.*附件简历/.test(normalized)
    || /预览附件简历/.test(normalized)
    || /查看附件简历/.test(normalized)
  );
}

export const CHAT_MESSAGE_ITEM_SELECTORS = Object.freeze([
  ".chat-message-list .message-item",
  ".message-list .message-item",
  ".conversation-message-list .message-item",
  ".chat-message-list [class*='message-item']",
  ".message-list [class*='message-item']",
  ".chat-record .message-item",
  ".chat-message-list > div",
  ".message-list > div"
]);

const RECRUITER_DOM_ROLE_PATTERN = /(?:item-my|item-me|message-boss|msg-boss|message-self|from-boss|from-hr|boss-chat|chat-boss)/i;
const CANDIDATE_DOM_ROLE_PATTERN = /(?:item-friend|item-geek|message-geek|msg-geek|from-geek|from-user|geek-chat|chat-geek)/i;
const HISTORY_MSG_URL_PATTERN = /\/wapi\/zpchat\/boss\/historyMsg\b/i;

function pickFirst(...values) {
  for (const value of values) {
    const normalized = typeof value === "string" ? normalizeText(value) : value;
    if (normalized !== "" && normalized != null) return normalized;
  }
  return "";
}

function normalizeList(value) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === "object") return Object.values(value);
  return [];
}

function parseNetworkBodyText(networkBody = {}) {
  const body = networkBody?.body;
  if (!body) return "";
  if (typeof body === "string") return body;
  if (typeof body?.body === "string") {
    return body.base64Encoded
      ? Buffer.from(body.body, "base64").toString("utf8")
      : body.body;
  }
  return "";
}

function tryParseJson(text = "") {
  const source = String(text || "").trim();
  if (!source) return null;
  try {
    return JSON.parse(source);
  } catch {
    return null;
  }
}

export function isSystemChatMessageText(text = "") {
  const normalized = normalizeText(text);
  if (!normalized) return true;
  if (isResumeRequestSentMessageText(normalized) || isResumeAttachmentMessageText(normalized)) {
    return true;
  }
  return Boolean(
    /对方更换了沟通职位|发送了面试邀请|拒绝了您的|系统消息|温馨提示|查看职位详情/.test(normalized)
    || /^(?:\[|【).*(?:\]|】)$/.test(normalized)
    || /^https?:\/\//i.test(normalized)
  );
}

export function inferChatMessageRoleFromDom(className = "", html = "") {
  const blob = `${className} ${String(html || "").slice(0, 400)}`;
  if (RECRUITER_DOM_ROLE_PATTERN.test(blob)) return "recruiter";
  if (CANDIDATE_DOM_ROLE_PATTERN.test(blob)) return "candidate";
  return "unknown";
}

export function inferChatMessageRoleFromNetwork(message = {}) {
  const from = message.from || message.sender || message.user || {};
  const source = Number(
    from.source ?? message.source ?? message.msgFrom ?? message.fromType ?? message.fromSource
  );
  if (source === 0) return "candidate";
  if (source === 1) return "recruiter";
  const role = normalizeText(from.role || message.role).toLowerCase();
  if (role.includes("geek") || role.includes("candidate")) return "candidate";
  if (role.includes("boss") || role.includes("recruiter") || role.includes("hr")) return "recruiter";
  if (message.geekId && !message.bossId) return "candidate";
  if (message.bossId && !message.geekId) return "recruiter";
  const flag = normalizeText(message.side || message.direction).toLowerCase();
  if (flag === "in" || flag === "receive" || flag === "received") return "candidate";
  if (flag === "out" || flag === "send" || flag === "sent") return "recruiter";
  return "unknown";
}

function extractTextFromHistoryMessage(message = {}) {
  const body = message.body || message.msg || message.content || {};
  return pickFirst(
    body.text,
    body.content,
    body.pushText,
    body.title,
    message.text,
    message.content,
    message.pushText
  );
}

export function extractBossChatHistoryTextMessages(payload = {}) {
  const messages = normalizeList(payload?.zpData?.messages).length
    ? normalizeList(payload?.zpData?.messages)
    : normalizeList(payload?.messages).length
      ? normalizeList(payload?.messages)
      : normalizeList(payload?.data?.messages).length
        ? normalizeList(payload?.data?.messages)
        : normalizeList(payload?.zpData?.data?.messages);
  const items = [];
  for (const message of messages) {
    const text = extractTextFromHistoryMessage(message);
    if (!text) continue;
    items.push({
      role: inferChatMessageRoleFromNetwork(message),
      text: normalizeText(text),
      source: "network_history_msg"
    });
  }
  return items;
}

export function extractGreetingMessagesFromNetworkBodies(networkBodies = []) {
  const items = [];
  for (const networkBody of networkBodies) {
    if (!HISTORY_MSG_URL_PATTERN.test(String(networkBody?.url || ""))) continue;
    const parsed = tryParseJson(parseNetworkBodyText(networkBody));
    if (!parsed) continue;
    items.push(...extractBossChatHistoryTextMessages(parsed));
  }
  return items;
}

export function cardPreviewTextFromCandidate(cardCandidate = null) {
  const raw = cardCandidate?.text?.raw || cardCandidate?.text || "";
  const lines = String(raw).split(/\r?\n/).map(normalizeText).filter(Boolean);
  if (!lines.length) return null;
  const name = normalizeText(cardCandidate?.identity?.name);
  const filtered = lines.filter((line) => line !== name && !/^\d+$/.test(line));
  if (!filtered.length) return null;
  return filtered[filtered.length - 1];
}

export function buildConversationPreview(messageItems = [], {
  cardPreviewText = null
} = {}) {
  const normalized = (messageItems || [])
    .map((item) => ({
      role: item?.role || "unknown",
      text: normalizeText(item?.text),
      source: item?.source || "conversation"
    }))
    .filter((item) => item.text && !isSystemChatMessageText(item.text));

  const candidateTexts = normalized
    .filter((item) => item.role === "candidate")
    .map((item) => item.text);
  let greetingText = candidateTexts[0] || null;
  let greetingTextSource = greetingText
    ? normalized.find((item) => item.role === "candidate" && item.text === greetingText)?.source || "conversation"
    : null;

  const preview = normalizeText(cardPreviewText);
  if (!greetingText && preview && !isSystemChatMessageText(preview)) {
    greetingText = preview;
    greetingTextSource = "card_preview";
  }

  return {
    greeting_text: greetingText || null,
    greeting_text_source: greetingTextSource,
    greeting_text_missing: !greetingText,
    card_preview_text: preview || null,
    message_count: normalized.length,
    candidate_message_count: candidateTexts.length,
    messages: normalized.slice(-12).map((item) => ({
      role: item.role,
      text: item.text.slice(0, 500),
      source: item.source
    }))
  };
}

export function parseChatMessagesFromHtml(html = "") {
  const source = String(html || "");
  if (!source) return [];
  const blockRegex = /<div\b[^>]*class=(["'])[^"']*\bmessage-item\b[^"']*\1[^>]*>([\s\S]*?)<\/div>/gi;
  const items = [];
  let match;
  while ((match = blockRegex.exec(source))) {
    const classMatch = /class=(["'])(.*?)\1/i.exec(match[0]);
    const className = classMatch?.[2] || "";
    const text = normalizeText(htmlToText(match[2]));
    if (!text) continue;
    items.push({
      role: inferChatMessageRoleFromDom(className, match[0]),
      text,
      source: "dom_message_list"
    });
  }
  return items;
}

export function mergeConversationPreview({
  networkBodies = [],
  domMessages = [],
  cardCandidate = null
} = {}) {
  const networkMessages = extractGreetingMessagesFromNetworkBodies(networkBodies);
  const merged = [];
  const seen = new Set();
  for (const item of [...networkMessages, ...domMessages]) {
    const key = `${item.role}:${item.text}`;
    if (seen.has(key)) continue;
    seen.add(key);
    merged.push(item);
  }
  return buildConversationPreview(merged, {
    cardPreviewText: cardPreviewTextFromCandidate(cardCandidate)
  });
}
