import { enqueue, moveTo, pendingCount, ping } from "../outbox.js";

const $ = (id) => document.getElementById(id);

const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
$("title").value = tab?.title ?? "";
$("url").value = tab?.url ?? "";

const pending = await pendingCount();
const online = await ping();
if (pending > 0) $("status").textContent = `${pending} kayit gonderilmeyi bekliyor`;
else if (!online) $("status").textContent = "forkOS kapali -- kayitlar kuyruga alinir";

$("save").addEventListener("click", async () => {
  $("save").disabled = true;
  const result = await enqueue({
    url: $("url").value,
    title: $("title").value,
    note: $("note").value || null,
    tags: $("tags").value.split(",").map((t) => t.trim()).filter(Boolean),
    collection: $("collection").value,
  });

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
