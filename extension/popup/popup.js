import {
  enqueue,
  enqueueTodo,
  enqueueNote,
  enqueueOpportunity,
  retryFailed,
  clearFailed,
  replaceFailed,
} from "../capture-client.js";
import { pendingCount, failedCount, failedCaptures, ping } from "../outbox.js";
import { getWebBase, getApiBase } from "../config.js";
import { deliveryText } from "../delivery.js";
import {
  collectPageDom,
  extractJobDetails,
  extractPageMetadata,
  extractAnnouncement,
} from "../extractor.js";
const $ = (id) => document.getElementById(id);
const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
const activeUrl = tab?.url ?? "",
  activeTitle = tab?.title ?? "";
for (const id of ["title", "todo-title", "note-title", "job-title"])
  $(id).value = activeTitle.slice(0, 300);
for (const id of ["url", "job-url"]) $(id).value = activeUrl;
let meta = null,
  lifecycle = null;
const tabs = ["bookmark", "todo", "note", "job"];
async function switchTab(name) {
  for (const mode of tabs) {
    $(`panel-${mode}`).hidden = mode !== name;
    $(`tab-${mode}`).classList.toggle("active", mode === name);
    $(`tab-${mode}`).setAttribute("aria-pressed", String(mode === name));
  }
  await chrome.storage.local.set({ captureTab: name });
  if (name === "job") await loadLifecycle();
}
for (const name of tabs)
  $(`tab-${name}`).addEventListener("click", () => void switchTab(name));
const { captureTab, captureCollection } = await chrome.storage.local.get([
  "captureTab",
  "captureCollection",
]);
if (tabs.includes(captureTab)) await switchTab(captureTab);
if (captureCollection) $("collection").value = captureCollection;
// Selection only: no expensive page-wide extraction until the user requests metadata.
if (tab?.id && /^https?:\/\//.test(activeUrl)) {
  try {
    const [r] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => String(window.getSelection() ?? "").slice(0, 6000),
    });
    $("note").value = r?.result ?? "";
    $("note-body").value = r?.result ?? "";
  } catch {
    $("status").textContent =
      "Bu sayfada metin seçimi okunamıyor; alanları elle doldurabilirsin.";
  }
} else
  $("status").textContent =
    "Bu tarayıcı sayfası yakalanamaz; bir HTTP(S) sayfası aç.";
const labels = {
  discovered: "Keşfedildi",
  shortlisted: "Kısa listede",
  new: "Yeni",
  reviewed: "İncelendi",
  watching: "Takipte",
  action_required: "Aksiyon gerekli",
  ignored: "Yoksayıldı",
  archived: "Arşivlendi",
};
async function loadLifecycle() {
  try {
    if (!lifecycle) {
      const r = await fetch(`${await getApiBase()}/opportunities/lifecycle`, {
        signal: AbortSignal.timeout(3000),
      });
      if (!r.ok) throw new Error();
      lifecycle = await r.json();
    }
    const kind = $("job-kind").value;
    const flow =
      lifecycle[kind === "job" ? "job_discovery" : "announcement"]?.flow ?? [];
    $("job-status").replaceChildren(
      ...flow
        .filter(
          (x) =>
            !["archived", "ignored", "dismissed", "closed", "expired"].includes(
              x,
            ),
        )
        .map((x) => {
          const o = document.createElement("option");
          o.value = x;
          o.textContent = labels[x] ?? x;
          return o;
        }),
    );
    $("job-save").disabled = !$("job-status").options.length;
  } catch {
    $("job-status").replaceChildren();
    $("job-save").disabled = true;
    $("status").textContent =
      "Fırsat durumları alınamadı; bağlantı gelince tekrar Kariyer / Akademi sekmesine bas.";
  }
}
$("job-kind").addEventListener("change", async () => {
  for (const id of [
    "job-org",
    "job-location",
    "job-compensation",
    "job-deadline",
    "job-published",
    "job-document",
    "job-notes",
  ])
    $(id).value = "";
  $("job-remote").value = "";
  $("source-confidence").textContent =
    "Kayıt türü kullanıcı tarafından seçildi; eksik alanlar bilinmiyor.";
  await loadLifecycle();
});
$("reextract-btn").addEventListener("click", async () => {
  if (!tab?.id || !/^https?:\/\//.test(activeUrl)) return;
  try {
    const [r] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: collectPageDom,
    });
    meta = extractPageMetadata(r.result, activeUrl);
    const data =
      $("job-kind").value === "job"
        ? extractJobDetails(r.result, activeUrl)
        : extractAnnouncement(r.result, activeUrl);
    for (const [key, id] of Object.entries({
      title: "job-title",
      organization: "job-org",
      location: "job-location",
      remote: "job-remote",
      compensation: "job-compensation",
      deadline_at: "job-deadline",
      published_at: "job-published",
      official_document_url: "job-document",
      notes: "job-notes",
    }))
      $(id).value = data[key] ?? "";
    $("source-confidence").textContent =
      `${data.sourceLabel ?? "Sayfa metaverisi"} · alanları doğrula; boş değerler bilinmiyor.`;
  } catch {
    $("status").textContent =
      "Sayfa metaverisi okunamadı; elle doldurabilirsin.";
  }
});
async function refresh() {
  const [pending, failed] = await Promise.all([pendingCount(), failedCount()]);
  $("pending-count").textContent = `${pending} bekleyen`;
  $("failed-count").textContent = `${failed} başarısız`;
  $("failed-actions").hidden = !failed;
  const list = $("failure-list");
  list.replaceChildren();
  for (const item of await failedCaptures()) {
    const div = document.createElement("div"),
      p = document.createElement("p"),
      edit = document.createElement("textarea"),
      btn = document.createElement("button");
    p.textContent = `${item.title || item.url} · ${item.message ?? "Reddedildi"}${item.replacement_id ? " · yeni yakalama oluşturuldu" : ""}`;
    edit.setAttribute("aria-label", "Başarısız yakalama içeriği");
    edit.value = JSON.stringify(item, null, 2);
    edit.maxLength = 60000;
    btn.textContent = "Düzeltmeyi yeni kimlikle gönder";
    btn.disabled = Boolean(item.replacement_id);
    btn.addEventListener("click", async () => {
      try {
        btn.disabled = true;
        const result = await replaceFailed(
          item.client_uuid,
          JSON.parse(edit.value),
        );
        $("status").textContent = deliveryText(result);
        await refresh();
      } catch {
        $("status").textContent =
          "Geçerli düzeltme JSON’u gerekli; önceki kayıt korunuyor.";
        btn.disabled = false;
      }
    });
    div.append(p, edit, btn);
    list.append(div);
  }
}
await refresh();
const online = await ping();
$("connection-badge").className =
  `badge badge-${online ? "online" : "offline"}`;
$("connection-text").textContent = online ? "Bağlı" : "Kuyruk modu";
$("open-options").addEventListener("click", () =>
  chrome.runtime.openOptionsPage(),
);
$("open-dashboard").addEventListener("click", async () =>
  chrome.tabs.create({ url: await getWebBase() }),
);
$("retry-failed").addEventListener("click", async () => {
  try {
    const r = await retryFailed();
    $("status").textContent =
      `${r.sent} teslim doğrulandı · ${r.pending} bekleyen · ${r.rejected.length} reddedilen`;
    await refresh();
  } catch {
    $("status").textContent =
      "Yeniden deneme tamamlanamadı; kayıtlar korunuyor.";
  }
});
$("clear-failed").addEventListener("click", async () => {
  if (
    !window.confirm(
      "Başarısız kayıtların yerel kopyaları kalıcı silinecek. Emin misin?",
    )
  )
    return;
  await clearFailed(true);
  await refresh();
});
const value = (id) => $(id).value.trim() || null;
function dateValue(id) {
  const text = value(id);
  if (text && !/T.*(Z|[+-]\d\d:\d\d)$/.test(text))
    throw new Error("Tarih saat dilimli ISO biçiminde olmalı");
  return text;
}
const forms = {
  bookmark: () =>
    enqueue({
      url: value("url"),
      title: value("title"),
      note: value("note"),
      tags: $("tags")
        .value.split(",")
        .map((t) => t.trim())
        .filter(Boolean),
      collection: $("collection").value,
      hero_image_url: meta?.image || null,
      favicon_url: meta?.favicon || null,
      author: meta?.author || null,
    }),
  todo: () =>
    enqueueTodo({
      title: value("todo-title"),
      priority: Number($("todo-priority").value),
      plan_day: value("todo-day"),
    }),
  note: () =>
    enqueueNote({
      title: value("note-title"),
      body_text: value("note-body") || "",
      folder: value("note-folder") || "general",
      url: activeUrl,
    }),
  job: () => {
    if (!$("job-status").value) throw new Error("Önce kanonik durumları yükle");
    return enqueueOpportunity({
      kind: $("job-kind").value,
      title: value("job-title"),
      organization: value("job-org"),
      url: value("job-url"),
      status: $("job-status").value,
      priority: Number($("job-priority").value),
      notes: value("job-notes"),
      deadline_at: dateValue("job-deadline"),
      published_at: dateValue("job-published"),
      location: value("job-location"),
      remote: value("job-remote"),
      compensation: value("job-compensation"),
      raw: {
        capture_evidence: {
          official_document_url: value("job-document"),
          source_confidence: "user_confirmed_page_metadata",
          missing_fields: [
            "organization",
            "published",
            "deadline",
            "document",
          ].filter(
            (key) => !value(`job-${key === "organization" ? "org" : key}`),
          ),
        },
      },
    });
  },
};
for (const [name, submit] of Object.entries(forms))
  $(`panel-${name}`).addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = $(`panel-${name}`).querySelector('[type="submit"]');
    button.disabled = true;
    $("status").textContent = "Kuyruğa kaydediliyor…";
    try {
      const result = await submit();
      $("status").textContent = deliveryText(result);
      await chrome.storage.local.set({
        captureCollection: $("collection").value,
      });
      await refresh();
    } catch (e) {
      $("status").textContent =
        e.message || "Kaydedilemedi; kuyruğu kontrol et.";
    } finally {
      button.disabled = false;
    }
  });
