import type { ReviewPreview } from "@/core/types";
import { reviewSecondarySignals } from "./reviewMetrics";

/** Pakete giren liste uzunluğu: paket özet taşır, döküm değil. */
const LIST_LIMIT = 20;

/**
 * Ajan için değerlendirme özeti (Markdown).
 *
 * SAF fonksiyon: pano/ağ/DOM erişimi yok, aynı girdi aynı metni üretir.
 * Paket VERİDİR, talimat değildir: sır, jeton, "şunu yap" metni veya başka
 * bir araca yapıştırma iması taşımaz. forkOS içinde gömülü bir sohbet yok;
 * bu paket hata ayıklama ve dışarıdaki ajanlar için tek tıkla bağlamdır.
 */
export function buildReviewDigest(data: ReviewPreview, note: string): string {
  const stats = data.stats;
  const out: string[] = [];

  out.push(`# Değerlendirme · ${data.kind === "weekly" ? "haftalık" : "günlük"}`);
  out.push("");
  out.push("## Dönem");
  out.push(`${data.period_start} → ${data.period_end}`);

  out.push("");
  out.push(`## Tamamlanan (${data.completed_todos.length})`);
  if (data.completed_todos.length === 0) {
    out.push("- yok");
  } else {
    for (const todo of data.completed_todos.slice(0, LIST_LIMIT)) {
      out.push(`- ${todo.title} · ${todo.completed_at}`);
    }
    if (data.completed_todos.length > LIST_LIMIT) {
      out.push(`- … ${data.completed_todos.length - LIST_LIMIT} kayıt daha`);
    }
  }

  out.push("");
  out.push(`## Açık (${data.unfinished_todos.length})`);
  if (data.unfinished_todos.length === 0) {
    out.push("- yok");
  } else {
    for (const todo of data.unfinished_todos.slice(0, LIST_LIMIT)) {
      out.push(`- ${todo.title} · ${todo.due_at ? `son tarih ${todo.due_at.slice(0, 10)}` : "son tarih yok"}`);
    }
    if (data.unfinished_todos.length > LIST_LIMIT) {
      out.push(`- … ${data.unfinished_todos.length - LIST_LIMIT} görev daha`);
    }
  }

  out.push("");
  out.push("## Odak");
  out.push(`- ${stats.focus.minutes} dk · ${stats.focus.sessions} seans · ${stats.focus.active_days} aktif gün`);
  if (stats.focus.best_day) {
    out.push(`- en iyi gün: ${stats.focus.best_day} (${stats.focus.best_day_minutes} dk)`);
  }
  if (stats.topics.length > 0) {
    out.push(`- konu dağılımı: ${stats.topics.map((topic) => `${topic.topic} ${topic.minutes} dk`).join(" · ")}`);
  }

  // Sıfır olan ikincil sinyal paketi şişirir: yalnız gerçekleşen hareket yazılır.
  const signals = reviewSecondarySignals(stats).filter((signal) => signal.value !== 0);
  out.push("");
  out.push("## Etkinlik öne çıkanları");
  if (signals.length === 0) {
    out.push("- kayıt yok");
  } else {
    for (const signal of signals) {
      out.push(`- ${signal.label}: ${signal.value}${signal.unit ? ` ${signal.unit}` : ""}`);
    }
  }

  out.push("");
  out.push("## Mevcut değerlendirme notu");
  out.push(note.trim() || "Not yok.");

  return out.join("\n");
}
