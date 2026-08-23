import {
  clearFailed,
  enqueue,
  failedCount,
  moveTo,
  pendingCount,
  ping,
  retryFailed,
} from "../outbox.js";

const $ = (id) => document.getElementById(id);

const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
$("title").value = tab?.title ?? "";
$("url").value = tab?.url ?? "";

async function refreshCounts() {
  const [pending, failed] = await Promise.all([pendingCount(), failedCount()]);
  $("pending-count").textContent = `${pending} bekleyen`;
  $("failed-count").textContent = `${failed} başarısız`;
  $("failed-actions").hidden = failed === 0;
  return { failed, pending };
}

const { pending } = await refreshCounts();
const online = await ping();
if (pending > 0) $("status").textContent = `${pending} kayit gonderilmeyi bekliyor`;
else if (!online) $("status").textContent = "forkOS kapali -- kayitlar kuyruga alinir";

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

$("save").addEventListener("click", async () => {
  $("save").disabled = true;
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
    $("save").disabled = false;
    return;
  }

  const duplicate = result.duplicates.find((d) => d.url === $("url").value);
  if (duplicate) {
    // Hata degil: ayni sayfayi ikinci kez kaydetmek serbest, sadece haber veriyoruz.
    $("status").textContent = "Kaydedildi";
    $("duplicate").hidden = false;
    $("move-learning").addEventListener("click", async () => {
      const ok = await moveTo(duplicate.existing_id, "learning");
      $("status").textContent = ok ? "Learning'e tasindi" : "Tasinamadi";
      setTimeout(() => window.close(), 600);
    });
    return;
  }

  $("status").textContent = result.pending ? "Kuyruga alindi (forkOS kapali)" : "Kaydedildi";
  setTimeout(() => window.close(), 700);
});
