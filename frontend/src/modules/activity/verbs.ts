/** Event verb -> insan diline cevirici. Yeni modul kendi verb'lerini buraya ekler. */
export const VERB_LABELS: Record<string, string> = {
  "bookmark.saved": "Yer imi kaydedildi",
  "bookmark.moved": "Yer imi taşındı",
  "bookmark.read": "Okundu işaretlendi",
  "bookmark.favorited": "Favori degisti",
  "bookmark.deleted": "Yer imi silindi",
  "rss.feed_added": "Besleme eklendi",
  "rss.feed_removed": "Besleme silindi",
  "rss.items_added": "Yeni RSS yazilari",
  "rss.item_read": "RSS yazisi okundu",
  "rss.item_saved": "RSS yazisi kaydedildi",
  "rss.marked_all_read": "Tümü okundu işaretlendi",
  "rss.feed_failed": "Besleme hata verdi",
  "rss.feed_disabled": "Besleme kapatıldı",
  "rss.pruned": "Eski yazilar temizlendi",
  "source.stalled": "Kaynak sessizlesti",
  "todo.created": "Görev oluşturuldu",
  "todo.completed": "Görev tamamlandı",
  "todo.dropped": "Görev bırakıldı",
  "todo.rescheduled": "Görev yeniden planlandı",
  "plan.scheduled": "Haftalık plana eklendi",
  "pomodoro.completed": "Odak tamamlandi",
  "pomodoro.interrupted": "Odak yarıda kesildi",
  "pomodoro.deleted": "Odak seansı silindi",
  "habit.checked": "Alışkanlık tamamlandı",
  "review.completed": "Değerlendirme tamamlandı",
  "opportunity.created": "Fırsat oluşturuldu",
  "opportunity.updated": "Fırsat güncellendi",
  "opportunity.items_added": "Yeni fırsatlar bulundu",
  "opportunity.trashed": "Fırsat çöpe taşındı",
  "opportunity.restored": "Fırsat geri yüklendi",
  "opportunity.deleted": "Fırsat kalıcı silindi",
  "source_sync.started": "Kaynak senkronizasyonu başladı",
  "source_sync.sources_added": "Senkronizasyona kaynak eklendi",
  "source_sync.completed": "Kaynak senkronizasyonu tamamlandı",
  "study.topic_completed": "Çalışma konusu tamamlandı",
  "study.confidence_changed": "Konu güveni güncellendi",
  "document.synced": "Belgeler eşitlendi",
  "calendar.synced": "Takvim eşitlendi",
  "calendar.plan_pushed": "Plan Google Calendar'a gönderildi",
  "project.created": "Proje oluşturuldu",
  "project.updated": "Proje güncellendi",
  "github.commit": "GitHub commit",
  "expense.created": "Harcama eklendi",
  "recurring_payment.created": "Düzenli ödeme eklendi",
  "recurring.paid": "Düzenli ödeme işlendi",
};

export const ALERT_VERBS = new Set([
  "source.stalled",
  "rss.feed_failed",
  "rss.feed_disabled",
]);

export function describe(verb: string, payload: Record<string, unknown>): string {
  const label = VERB_LABELS[verb] ?? verb;
  const move = payload.to ? `${payload.from ?? "?"} → ${payload.to}` : undefined;
  const detail =
    (payload.message as string | undefined) ??
    move ??
    (payload.title as string | undefined) ??
    (payload.url as string | undefined) ??
    "";
  const count = payload.count ? ` (${payload.count})` : "";
  return `${label}${count}${detail ? ` — ${detail}` : ""}`;
}
