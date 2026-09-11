import {
  clearFailed,
  enqueue,
  enqueueNote,
  enqueueOpportunity,
  enqueueTodo,
  failedCount,
  moveTo,
  pendingCount,
  ping,
  retryFailed,
} from "../outbox.js";
import { collectPageDom, extractJobDetails, extractPageMetadata } from "../extractor.js";

const $ = (id) => document.getElementById(id);

// Sekme sorgusu ve alanları doldurma
const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
const activeTitle = tab?.title ?? "";
const activeUrl = tab?.url ?? "";

// Form varsayılanlarını doldur
$("title").value = activeTitle;
$("url").value = activeUrl;
$("job-url").value = activeUrl;
$("todo-title").value = activeTitle;
$("note-title").value = activeTitle;

let lastExtracted = null;
let lastPageMeta = null;

// 4 Sekmeli geçiş fonksiyonları
const tabs = ["bookmark", "todo", "note", "job"];

function switchTab(activeName) {
  for (const name of tabs) {
    const tabBtn = $(`tab-${name}`);
    const panel = $(`panel-${name}`);
    if (!tabBtn || !panel) continue;
    if (name === activeName) {
      tabBtn.classList.add("active");
      panel.hidden = false;
    } else {
      tabBtn.classList.remove("active");
      panel.hidden = true;
    }
  }
}

$("tab-bookmark").addEventListener("click", () => switchTab("bookmark"));
$("tab-todo").addEventListener("click", () => switchTab("todo"));
$("tab-note").addEventListener("click", () => switchTab("note"));
$("tab-job").addEventListener("click", () => {
  switchTab("job");
  if (!lastExtracted) {
    inspectPageForJob();
  }
});

$("reextract-btn").addEventListener("click", async () => {
  $("extraction-text").textContent = "Sayfa taranıyor…";
  await inspectPageForJob();
});

// Sayfayı deterministik olarak tara (JSON-LD, ATS, Meta)
async function inspectPageForJob() {
  if (!tab?.id || !activeUrl || (!activeUrl.startsWith("http://") && !activeUrl.startsWith("https://"))) {
    return;
  }

  try {
    const [injection] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: collectPageDom,
    });

    if (injection?.result) {
      // Sayfa meta verilerini çıkar ve not/alıntı alanlarına yerleştir
      const pageMeta = extractPageMetadata(injection.result, activeUrl);
      lastPageMeta = pageMeta;
      if (pageMeta.selectedText) {
        if (!$("note").value) $("note").value = pageMeta.selectedText;
        if (!$("note-body").value) $("note-body").value = pageMeta.selectedText;
      } else if (pageMeta.description && !$("note").value) {
        $("note").placeholder = pageMeta.description.slice(0, 150) + "…";
      }

      const details = extractJobDetails(injection.result, activeUrl);
      if (details.found) {
        lastExtracted = details;
        if (details.title) $("job-title").value = details.title;
        if (details.organization) $("job-org").value = details.organization;
        if (details.location) $("job-location").value = details.location;
        if (details.remote) $("job-remote").value = details.remote;
        if (details.compensation) $("job-compensation").value = details.compensation;
        if (details.deadline_at) $("job-deadline").value = details.deadline_at;
        if (details.notes) $("job-notes").value = details.notes;

        $("extraction-badge").hidden = false;
        $("extraction-text").textContent = `[${details.sourceLabel}] ile tespit edildi`;

        // Güçlü bir iş ilanı kaynağı (JSON-LD veya ATS) tespit edildiyse otomatik iş ilanı sekmesine geç
        if (details.sourceType === "schema_org" || details.sourceType === "ats") {
          switchTab("job");
        }
      }
    }
  } catch (err) {
    console.debug("forkOS: Sayfa script analizi yapılamadı (izin veya sayfa kısıtı)", err);
  }
}

// İlk açılışta sayfayı tara
await inspectPageForJob();

// Kuyruk ve Bağlantı Durumu
async function refreshCounts() {
  const [pending, failed] = await Promise.all([pendingCount(), failedCount()]);
  $("pending-count").textContent = `${pending} bekleyen`;
  $("failed-count").textContent = `${failed} başarısız`;
  $("failed-actions").hidden = failed === 0;
  return { failed, pending };
}

async function checkConnection() {
  const online = await ping();
  const badge = $("connection-badge");
  const text = $("connection-text");
  if (online) {
    badge.className = "badge badge-online";
    text.textContent = "Bağlı";
  } else {
    badge.className = "badge badge-offline";
    text.textContent = "Kuyrukta (Offline)";
  }
  return online;
}

const { pending } = await refreshCounts();
const online = await checkConnection();

if (pending > 0) {
  $("status").textContent = `${pending} kayıt gönderilmeyi bekliyor`;
} else if (!online) {
  $("status").textContent = "forkOS çevrimdışı — kayıtlar yerel kuyruğa alınır";
}

// Buton aksiyonları
$("retry-failed").addEventListener("click", async () => {
  $("status").textContent = "Yeniden deneniyor…";
  const result = await retryFailed();
  await refreshCounts();
  $("status").textContent = result.pending
    ? `${result.pending} kayıt hâlâ bekliyor`
    : "Başarısız kayıtlar yeniden gönderildi";
});

$("clear-failed").addEventListener("click", async () => {
  await clearFailed();
  await refreshCounts();
  $("status").textContent = "Başarısız kayıtlar temizlendi";
});

$("open-options").addEventListener("click", () => chrome.runtime.openOptionsPage());

$("open-dashboard").addEventListener("click", () => {
  chrome.tabs.create({ url: "http://127.0.0.1:5173" });
});

// Form 1: Bağlantı Kaydet
$("panel-bookmark").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("save");
  btn.disabled = true;
  $("status").textContent = "Kaydediliyor…";

  try {
    const result = await enqueue({
      url: $("url").value,
      title: $("title").value,
      note: $("note").value || null,
      tags: $("tags").value.split(",").map((t) => t.trim()).filter(Boolean),
      collection: $("collection").value,
      hero_image_url: lastPageMeta?.image || null,
      favicon_url: lastPageMeta?.favicon || null,
      reading_time_min: lastPageMeta?.readingTimeMinutes || null,
      author: lastPageMeta?.author || null,
    });

    const rejected = result.rejected.find((entry) => entry.url === $("url").value);
    if (rejected) {
      $("status").textContent = `Kaydedilemedi: ${rejected.message}`;
      btn.disabled = false;
      return;
    }

    const duplicate = result.duplicates.find((d) => d.url === $("url").value);
    if (duplicate) {
      $("status").textContent = "Kaydedildi (mükerrer kayıt)";
      $("duplicate").hidden = false;
      $("move-learning").addEventListener("click", async () => {
        const ok = await moveTo(duplicate.existing_id, "learning");
        $("status").textContent = ok ? "Learning'e taşındı" : "Taşınamadı";
        setTimeout(() => window.close(), 600);
      });
      return;
    }

    $("status").textContent = result.pending ? "Kuyruğa alındı (forkOS kapalı)" : "Kütüphaneye kaydedildi!";
    setTimeout(() => window.close(), 700);
  } catch (err) {
    btn.disabled = false;
    $("status").textContent = `Kaydedilemedi: ${err?.message ?? err}`;
  }
});

// Form 2: İş İlanı Kaydet
$("panel-job").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("job-save");
  const jobTitle = $("job-title").value.trim();
  if (!jobTitle) return;

  btn.disabled = true;
  $("status").textContent = "İş ilanı ekleniyor…";

  try {
    const result = await enqueueOpportunity({
      title: jobTitle,
      organization: $("job-org").value.trim() || null,
      url: $("job-url").value.trim() || null,
      remote: $("job-remote").value || null,
      location: $("job-location").value.trim() || null,
      compensation: $("job-compensation").value.trim() || null,
      deadline_at: $("job-deadline").value.trim() || null,
      status: $("job-status").value || "discovered",
      priority: Number($("job-priority").value) || 2,
      notes: $("job-notes").value.trim() || null,
    });

    const rejected = result.rejected.find((entry) => entry.url === $("job-url").value);
    if (rejected) {
      $("status").textContent = `Eklenemedi: ${rejected.message}`;
      btn.disabled = false;
      return;
    }

    $("status").textContent = result.pending ? "Kuyruğa alındı (forkOS kapalı)" : "Fırsat olarak eklendi!";
    setTimeout(() => window.close(), 700);
  } catch (err) {
    btn.disabled = false;
    $("status").textContent = `Eklenemedi: ${err?.message ?? err}`;
  }
});

// Form 3: Görev Kaydet
$("panel-todo").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("todo-save");
  const title = $("todo-title").value.trim();
  if (!title) return;

  btn.disabled = true;
  $("status").textContent = "Görev ekleniyor…";

  try {
    const result = await enqueueTodo({
      title,
      priority: Number($("todo-priority").value) || 2,
      plan_day: $("todo-day").value || null,
    });

    $("status").textContent = result.pending ? "Kuyruğa alındı (forkOS kapalı)" : "Görev eklendi!";
    setTimeout(() => window.close(), 700);
  } catch (err) {
    btn.disabled = false;
    $("status").textContent = `Eklenemedi: ${err?.message ?? err}`;
  }
});

// Form 4: Not Kaydet
$("panel-note").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("note-save");
  const title = $("note-title").value.trim();
  if (!title) return;

  btn.disabled = true;
  $("status").textContent = "Not kaydediliyor…";

  try {
    const result = await enqueueNote({
      title,
      body_text: $("note-body").value.trim(),
      folder: $("note-folder").value.trim() || "general",
    });

    $("status").textContent = result.pending ? "Kuyruğa alındı (forkOS kapalı)" : "Not kaydedildi!";
    setTimeout(() => window.close(), 700);
  } catch (err) {
    btn.disabled = false;
    $("status").textContent = `Kaydedilemedi: ${err?.message ?? err}`;
  }
});

