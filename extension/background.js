import { enqueue, flush } from "./outbox.js";
import { RETRY_MINUTES } from "./config.js";

const MENUS = [
  { id: "save-page", title: "forkOS: sayfayi kaydet", contexts: ["page"] },
  { id: "save-selection", title: "forkOS: secimi kaydet", contexts: ["selection"] },
  { id: "save-link", title: "forkOS: linki kaydet", contexts: ["link"] },
];

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => MENUS.forEach((m) => chrome.contextMenus.create(m)));
  chrome.alarms.create("flush", { periodInMinutes: RETRY_MINUTES });
  flush();
});

// Tarayici acilisi = backend'in de acilmis olma ihtimali; bekleyenleri gonder.
chrome.runtime.onStartup.addListener(flush);
chrome.alarms.onAlarm.addListener((alarm) => alarm.name === "flush" && flush());

async function flash(text, color) {
  await chrome.action.setBadgeBackgroundColor({ color });
  await chrome.action.setBadgeText({ text });
  setTimeout(() => flush(), 1500);   // rozet sayaci flush icinde yeniden yazilir
}

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "quick-save") return;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) return;
  const result = await enqueue({ url: tab.url, title: tab.title ?? "" });
  const rejected = result.rejected.length > 0;
  await flash(rejected ? "!" : result.pending ? "⏳" : "✓", rejected ? "#b91c1c" : result.pending ? "#b45309" : "#166534");
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const url = info.linkUrl ?? info.pageUrl ?? tab?.url ?? "";
  if (!url) return;
  const result = await enqueue({
    url,
    title: tab?.title ?? "",
    selection: info.selectionText ?? null,
  });
  const rejected = result.rejected.length > 0;
  await flash(rejected ? "!" : result.pending ? "⏳" : "✓", rejected ? "#b91c1c" : result.pending ? "#b45309" : "#166534");
});
