import {
  clearFailed,
  enqueue,
  enqueueOpportunity,
  failedCount,
  moveTo,
  pendingCount,
  ping,
  retryFailed,
} from "../outbox.js";
import { collectPageDom, extractJobDetails } from "../extractor.js";

const $ = (id) => document.getElementById(id);

// Sekme sorgusu ve alanları doldurma
const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
const activeTitle = tab?.title ?? "";
const activeUrl = tab?.url ?? "";

// Bookmark formunu doldur
$("title").value = activeTitle;
$("url").value = activeUrl;
$("job-url").value = activeUrl;

let lastExtracted = null;

// Sekme geçiş fonksiyonları
function switchToJobTab() {
  $("tab-job").classList.add("active");
  $("tab-bookmark").classList.remove("active");
  $("panel-job").hidden = false;
  $("panel-bookmark").hidden = true;
}

function switchToBookmarkTab() {
  $("tab-bookmark").classList.add("active");
  $("tab-job").classList.remove("active");
  $("panel-bookmark").hidden = false;
  $("panel-job").hidden = true;
}

$("tab-bookmark").addEventListener("click", switchToBookmarkTab);
$("tab-job").addEventListener("click", () => {
  switchToJobTab();
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
        $("extraction-text").textContent = `✨ ${details.sourceLabel} ile tespit edildi`;

        // Güçlü bir iş ilanı kaynağı (JSON-LD veya ATS) tespit edildiyse otomatik iş ilanı sekmesine geç
        if (details.sourceType === "schema_org" || details.sourceType === "ats") {
          switchToJobTab();
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

