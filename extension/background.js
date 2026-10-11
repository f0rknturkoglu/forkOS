import {
  enqueue,
  enqueueOpportunity,
  flush,
  retryFailed,
  clearFailed,
  replaceFailed,
} from "./outbox.js";
import { collectPageDom, extractJobDetails } from "./extractor.js";
import { RETRY_MINUTES } from "./config.js";

const MENUS = [
  { id: "save-page", title: "forkOS: sayfayı kaydet", contexts: ["page"] },
  {
    id: "save-opportunity",
    title: "forkOS: bu sayfayı iş ilanı olarak kaydet",
    contexts: ["page"],
  },
  {
    id: "save-selection",
    title: "forkOS: seçimi kaydet",
    contexts: ["selection"],
  },
  { id: "save-link", title: "forkOS: linki kaydet", contexts: ["link"] },
];

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() =>
    MENUS.forEach((m) => chrome.contextMenus.create(m)),
  );
  chrome.alarms.create("flush", { periodInMinutes: RETRY_MINUTES });
  flush();
});

// Tarayici acilisi = backend'in de acilmis olma ihtimali; bekleyenleri gonder.
chrome.runtime.onStartup.addListener(flush);
chrome.alarms.onAlarm.addListener((alarm) => alarm.name === "flush" && flush());

async function flash(text, color) {
  await chrome.action.setBadgeBackgroundColor({ color });
  await chrome.action.setBadgeText({ text });
  // Rozet sayaci flush icinde yeniden yazilir; gecikme geri bildirimi
  // gosterir, hatalar burada yakalanir (unhandled rejection yok).
  await new Promise((resolve) => setTimeout(resolve, 1500));
  await flush().catch((err) => console.error("forkOS: flush hatasi", err));
}

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "quick-save") return;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) return;
  const result = await enqueue({ url: tab.url, title: tab.title ?? "" });
  const rejected = ![
    "saved",
    "already_present",
    "queued_offline",
    "retry_pending",
    "unknown_delivery",
  ].includes(result.capture?.state);
  await flash(
    rejected ? "!" : result.pending ? "⏳" : "✓",
    rejected ? "#b91c1c" : result.pending ? "#b45309" : "#166534",
  );
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const url = info.linkUrl ?? info.pageUrl ?? tab?.url ?? "";
  if (!url) return;

  if (info.menuItemId === "save-opportunity") {
    let jobDetails = null;
    if (tab?.id && url.startsWith("http")) {
      try {
        const [injection] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: collectPageDom,
        });
        if (injection?.result) {
          jobDetails = extractJobDetails(injection.result, url);
        }
      } catch (err) {
        console.debug("forkOS: context menu extract failed", err);
      }
    }

    const result = await enqueueOpportunity({
      title: jobDetails?.title || tab?.title || "İş İlanı",
      organization: jobDetails?.organization || null,
      url,
      remote: jobDetails?.remote || null,
      location: jobDetails?.location || null,
      compensation: jobDetails?.compensation || null,
      deadline_at: jobDetails?.deadline_at || null,
      status: "discovered",
      priority: 2,
      notes: jobDetails?.notes || info.selectionText || null,
    });
    const rejected = ![
      "saved",
      "already_present",
      "queued_offline",
      "retry_pending",
      "unknown_delivery",
    ].includes(result.capture?.state);
    await flash(
      rejected ? "!" : result.pending ? "⏳" : "✓",
      rejected ? "#b91c1c" : result.pending ? "#b45309" : "#166534",
    );
    return;
  }

  const result = await enqueue({
    url,
    title: tab?.title ?? "",
    selection: info.selectionText ?? null,
  });
  const rejected = ![
    "saved",
    "already_present",
    "queued_offline",
    "retry_pending",
    "unknown_delivery",
  ].includes(result.capture?.state);
  await flash(
    rejected ? "!" : result.pending ? "⏳" : "✓",
    rejected ? "#b91c1c" : result.pending ? "#b45309" : "#166534",
  );
});

// Single storage writer across popup and worker contexts. Never accept website messages.
const ACTIONS = { enqueue, retryFailed, clearFailed, replaceFailed };
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (
    sender.id !== chrome.runtime.id ||
    sender.tab ||
    message?.type !== "forkos.capture"
  )
    return false;
  const action = Object.hasOwn(ACTIONS, message.action)
    ? ACTIONS[message.action]
    : null;
  if (
    !action ||
    !Array.isArray(message.args) ||
    JSON.stringify(message).length > 64000
  ) {
    respond({ ok: false, error: "Geçersiz yakalama isteği" });
    return false;
  }
  action(...message.args).then(
    (result) => respond({ ok: true, result }),
    () =>
      respond({
        ok: false,
        error: "Yakalama tamamlanamadı; kuyruk ve hata kayıtları korunuyor.",
      }),
  );
  return true;
});
