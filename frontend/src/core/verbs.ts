/**
 * Event verb -> insan diline cevirici. Yeni modul kendi verb'lerini buraya ekler.
 *
 * Uyari (alerts) kurali BURADA DEGIL: hangi kaydin dikkat gerektirdigi
 * sunucuda tek yerde durur (backend/app/core/events.py) ve akis yanitinda
 * `is_alert` bayragi olarak gelir -- istemci ikinci bir liste tutmaz.
 */
import type { LucideIcon } from "lucide-react";
import {
  Bookmark,
  Calendar,
  CircleDot,
  ClipboardCheck,
  Compass,
  DatabaseBackup,
  FileText,
  Film,
  GitCommitHorizontal,
  GraduationCap,
  Layers,
  Link2,
  ListChecks,
  RefreshCw,
  Rss,
  SlidersHorizontal,
  StickyNote,
  Timer,
  Wallet,
} from "lucide-react";

/**
 * Kanonik fiil defteri (backend/app/core/registry.py + modul event_verbs)
 * ile BIREBIR kapsanir; guard testi (verbsLabels.test.ts) yeni bir fiil
 * etiketsiz kalirsa duser. Uslup: gecmis zaman, ilk harf buyuk, noktalama yok.
 */
export const VERB_LABELS: Record<string, string> = {
  // Yer imleri
  "bookmark.saved": "Yer imi kaydedildi",
  "bookmark.moved": "Yer imi taşındı",
  "bookmark.read": "Okundu işaretlendi",
  "bookmark.favorited": "Favori değişti",
  "bookmark.deleted": "Yer imi silindi",
  "bookmark.highlighted": "Alıntı işaretlendi",
  "bookmark.scrolled": "Okuma ilerlemesi kaydedildi",
  // RSS
  "rss.feed_added": "Besleme eklendi",
  "rss.feed_removed": "Besleme silindi",
  "rss.items_added": "Yeni RSS yazıları",
  "rss.item_read": "RSS yazısı okundu",
  "rss.item_saved": "RSS yazısı kaydedildi",
  "rss.marked_all_read": "Tümü okundu işaretlendi",
  "rss.feed_failed": "Besleme hata verdi",
  "rss.feed_disabled": "Besleme kapatıldı",
  "rss.pruned": "Eski yazılar temizlendi",
  // Notlar
  "note.created": "Not oluşturuldu",
  "note.updated": "Not güncellendi",
  "note.pinned": "Not sabitlendi",
  "note.archived": "Not arşivlendi",
  "note.trashed": "Not çöpe taşındı",
  "note.restored": "Not geri yüklendi",
  "note.archive_restored": "Not arşivden çıkarıldı",
  "note.source_linked": "Nota kaynak bağlandı",
  "note.moved": "Not taşındı",
  "note.deleted": "Not kalıcı silindi",
  "note.attachment_added": "Nota ek eklendi",
  "note.attachment_deleted": "Not eki silindi",
  "note.folder_created": "Not klasörü oluşturuldu",
  "note.folder_updated": "Not klasörü güncellendi",
  "note.folder_deleted": "Not klasörü silindi",
  // Görevler ve plan
  "todo.created": "Görev oluşturuldu",
  "todo.completed": "Görev tamamlandı",
  "todo.dropped": "Görev bırakıldı",
  "todo.rescheduled": "Görev yeniden planlandı",
  "plan.scheduled": "Haftalık plana eklendi",
  "plan.rescheduled": "Plan yeniden zamanlandı",
  "plan.unscheduled": "Plandan çıkarıldı",
  "plan.carried_over": "Plan sonraki haftaya taşındı",
  // Odak
  "pomodoro.completed": "Odak tamamlandı",
  "pomodoro.interrupted": "Odak yarıda kesildi",
  "pomodoro.deleted": "Odak seansı silindi",
  // Değerlendirme
  "review.completed": "Değerlendirme tamamlandı",
  "review.note_updated": "Değerlendirme notu güncellendi",
  "goal.created": "Hedef oluşturuldu",
  "goal.updated": "Hedef güncellendi",
  "goal.milestone_added": "Hedef kilometre taşı eklendi",
  "goal.milestone_updated": "Hedef kilometre taşı güncellendi",
  "career_proposal.created": "Kariyer önerisi hazırlandı",
  "career_proposal.approved": "Kariyer önerisi onaylandı",
  "career_proposal.rejected": "Kariyer önerisi reddedildi",
  "career_proposal.materialized": "Kariyer önerisi kayda dönüştürüldü",
  "career_proposal.unsupported": "Kariyer önerisi uygulanamadı",
  "career_proposal.expired": "Kariyer önerisinin süresi doldu",
  // Çalışma, kurs ve öğrenme kaynakları
  "study.area_created": "Çalışma alanı oluşturuldu",
  "study.area_archived": "Çalışma alanı arşivlendi",
  "study.area_reopened": "Çalışma alanı yeniden açıldı",
  "study.area_deleted": "Çalışma alanı silindi",
  "study.topic_created": "Çalışma konusu oluşturuldu",
  "study.topic_renamed": "Çalışma konusu yeniden adlandırıldı",
  "study.topic_moved": "Çalışma konusu taşındı",
  "study.topic_started": "Çalışma konusu başladı",
  "study.topic_reopened": "Çalışma konusu yeniden açıldı",
  "study.topic_completed": "Çalışma konusu tamamlandı",
  "study.topic_deleted": "Çalışma konusu silindi",
  "study.confidence_changed": "Konu güveni güncellendi",
  "study.mastery_changed": "Konu ustalığı güncellendi",
  "study.reviewed": "Konu tekrar edildi",
  "course.created": "Kurs oluşturuldu",
  "course.started": "Kursa başlandı",
  "course.progressed": "Kurs ilerledi",
  "course.completed": "Kurs tamamlandı",
  "course.reopened": "Kurs yeniden açıldı",
  "course.deleted": "Kurs silindi",
  "learning.imported": "Öğrenme içeriği içe aktarıldı",
  "learning.resource_added": "Öğrenme kaynağı eklendi",
  "learning.resource_updated": "Öğrenme kaynağı güncellendi",
  "learning.resource_completed": "Öğrenme kaynağı tamamlandı",
  "learning.resource_reopened": "Öğrenme kaynağı yeniden açıldı",
  "learning.resource_deleted": "Öğrenme kaynağı silindi",
  // Kart tekrarı
  "flashcard.deck_created": "Deste oluşturuldu",
  "flashcard.card_added": "Kart eklendi",
  "flashcard.reviewed": "Kart tekrar edildi",
  "flashcard.imported": "Kartlar içe aktarıldı",
  // Medya
  "media.item_added": "Medya eklendi",
  "media.item_updated": "Medya güncellendi",
  "media.item_trashed": "Medya çöpe taşındı",
  "media.item_restored": "Medya geri yüklendi",
  "media.item_deleted": "Medya kalıcı silindi",
  "media.cycle_started": "Medya döngüsü başladı",
  "media.cycle_completed": "Medya döngüsü tamamlandı",
  "media.cycle_reopened": "Medya döngüsü yeniden açıldı",
  "media.consumed": "Medya tüketildi",
  "media.session_logged": "İzleme oturumu kaydedildi",
  "media.progress_corrected": "Medya ilerlemesi düzeltildi",
  "media.status_changed": "Medya durumu değişti",
  "media.collection_created": "Koleksiyon oluşturuldu",
  "media.collection_updated": "Koleksiyon güncellendi",
  "media.collection_deleted": "Koleksiyon silindi",
  "media.collection_item_added": "Koleksiyona medya eklendi",
  "media.collection_item_removed": "Koleksiyondan medya çıkarıldı",
  "media.release_discovered": "Yeni yayın bulundu",
  "media.sync_completed": "Medya senkronizasyonu tamamlandı",
  "media.sync_failed": "Medya senkronizasyonu başarısız",
  "media.sync_empty": "Medya senkronizasyonu boş döndü",
  "media.artwork_pruned": "Eski görseller temizlendi",
  // Fırsatlar ve kariyer
  "opportunity.created": "Fırsat oluşturuldu",
  "opportunity.updated": "Fırsat güncellendi",
  "opportunity.status_changed": "Başvuru durumu değişti",
  "opportunity.trashed": "Fırsat çöpe taşındı",
  "opportunity.restored": "Fırsat geri yüklendi",
  "opportunity.deleted": "Fırsat kalıcı silindi",
  "opportunity.pruned": "Eski fırsatlar temizlendi",
  "opportunity.items_added": "Yeni fırsatlar bulundu",
  "opportunity.duplicates_merged": "Yinelenen kayıtlar birleştirildi",
  "opportunity.evaluated": "Fırsat değerlendirildi",
  "opportunity.package_prepared": "Başvuru paketi üretildi",
  "opportunity.package_cover_reviewed": "Başvuru ön yazısı incelendi",
  "opportunity.interview_prepared": "Görüşme hazırlığı oluşturuldu",
  "opportunity.interview_practiced": "Görüşme provası kaydedildi",
  "opportunity.interview_debriefed": "Görüşme değerlendirmesi kaydedildi",
  "opportunity.package_answer_resolved": "Başvuru sorusu kullanıcı tarafından yanıtlandı",
  "opportunity.evaluation_updated": "Fırsat değerlendirmesi güncellendi",
  "opportunity.interview_added": "Mülakat eklendi",
  "opportunity.interview_updated": "Mülakat güncellendi",
  "opportunity.interview_deleted": "Mülakat silindi",
  "opportunity.requirement_added": "İlan şartı eklendi",
  "opportunity.requirement_document_bound": "Şarta belge bağlandı",
  "opportunity.source_reopened": "Kaynak yeniden açıldı",
  "opportunity.source_status_changed": "Kaynak durumu değişti",
  "career_story.created": "Kariyer hikayesi oluşturuldu",
  "career_story.updated": "Kariyer hikayesi güncellendi",
  "career_story.archived": "Kariyer hikayesi arşivlendi",
  "career_connections.imported": "Kariyer bağlantıları içe aktarıldı",
  // Projeler
  "project.created": "Proje oluşturuldu",
  "project.updated": "Proje güncellendi",
  "project.deleted": "Proje silindi",
  "project.milestone_added": "Kilometre taşı eklendi",
  "project.milestone_updated": "Kilometre taşı güncellendi",
  "project.milestone_deleted": "Kilometre taşı silindi",
  "github.commit": "GitHub commit",
  // Finans
  "expense.created": "Harcama eklendi",
  "expense.deleted": "Harcama silindi",
  "income.created": "Gelir eklendi",
  "income.deleted": "Gelir silindi",
  "recurring_payment.created": "Düzenli ödeme eklendi",
  "recurring_payment.deleted": "Düzenli ödeme silindi",
  "recurring.paid": "Düzenli ödeme işlendi",
  // Belgeler ve takvim
  "document.created": "Belge oluşturuldu",
  "document.deleted": "Belge silindi",
  "document.synced": "Belgeler eşitlendi",
  "calendar.synced": "Takvim eşitlendi",
  "calendar.plan_pushed": "Plan Google Calendar'a gönderildi",
  // Bağlantılar ve kaynaklar
  "link.created": "Kayıtlar arasında bağlantı kuruldu",
  "source.stalled": "Kaynak sessizleşti",
  "source.failing": "Kaynak hata veriyor",
  "source_sync.queued": "Kaynak senkronizasyonu kuyruğa alındı",
  "source_sync.started": "Kaynak senkronizasyonu başladı",
  "source_sync.sources_added": "Senkronizasyona kaynak eklendi",
  "source_sync.completed": "Kaynak senkronizasyonu tamamlandı",
  // Yedek, ayarlar ve sistem
  "backup.created": "Yedek oluşturuldu",
  "backup.restored": "Yedek geri yüklendi",
  "backup.drive_uploaded": "Yedek Drive'a yüklendi",
  "backup.drive_upload_failed": "Yedek Drive'a yüklenemedi",
  "settings.updated": "Ayar güncellendi",
  "settings.reset": "Ayarlar sıfırlandı",
  "system.refresh.started": "Sistem yenilemesi başladı",
  "system.refresh.completed": "Sistem yenilemesi tamamlandı",
  "system.maintenance": "Sistem bakımı çalıştı",
  "system.automation_profile": "Otomasyon profili değişti",
  // A4 — Semantik hafıza adayı
  "semantic_candidate.confirmed": "Hafıza adayı onaylandı",
  "semantic_candidate.promoted": "Hafıza adayı kalıcı bilgiye terfi etti",
  "semantic_candidate.rejected": "Hafıza adayı reddedildi",
  "semantic_candidate.stale": "Hafıza adayı kaynağı güncelliğini yitirdi",
  // Modulu kaldirilmis eski fiiller: event tablosu append-only oldugu icin
  // gecmis satirlar hala gorunur (bkz. backend review/service.py habit notu).
  "habit.checked": "Rutin işaretlendi",
  "habit.deleted": "Rutin silindi",
  "book.deleted": "Kitap silindi",
};

/**
 * Fiil ailesi (namespace) -> ikon. Akis satirinda cumlenin solunda durur:
 * "bu ne tur bir kayit?" sorusunu okumadan once yanitlar. En uzun eslesen
 * aile kazanir ("recurring.paid" -> "recurring"), bilinmeyen fiil notr
 * ikonla cizilir -- yeni bir modul ikon eklemeyi unutsa akis bozulmaz.
 */
const VERB_ICONS: Record<string, LucideIcon> = {
  todo: ListChecks,
  plan: ListChecks,
  pomodoro: Timer,
  review: ClipboardCheck,
  study: GraduationCap,
  course: GraduationCap,
  learning: GraduationCap,
  flashcard: Layers,
  bookmark: Bookmark,
  rss: Rss,
  media: Film,
  note: StickyNote,
  opportunity: Compass,
  career_story: Compass,
  career_connections: Compass,
  document: FileText,
  project: Layers,
  expense: Wallet,
  income: Wallet,
  recurring: Wallet,
  recurring_payment: Wallet,
  calendar: Calendar,
  source: RefreshCw,
  source_sync: RefreshCw,
  backup: DatabaseBackup,
  system: SlidersHorizontal,
  settings: SlidersHorizontal,
  link: Link2,
  "github.commit": GitCommitHorizontal,
};

export function verbIcon(verb: string): LucideIcon {
  let candidate = verb;
  while (candidate) {
    const icon = VERB_ICONS[candidate];
    if (icon) return icon;
    const cut = candidate.lastIndexOf(".");
    if (cut <= 0) break;
    candidate = candidate.slice(0, cut);
  }
  return CircleDot;
}

/**
 * NEDEN yedek var: kanonik deftere (backend registry) yeni bir fiil eklenip
 * etiketi unutulursa akis ham `modul.snake_case_fiil` anahtarini gostermemeli.
 * Onek atilir, alt cizgiler bosluga cevrilir, ilk harf buyutulur. Bu yedek
 * yalnizca "bos satir olmasin" icindir; DOGRU cozum VERB_LABELS'a etiket
 * eklemektir -- guard testi (verbsLabels.test.ts) bunu zorlar.
 */
function readableFallback(verb: string): string {
  const cut = verb.lastIndexOf(".");
  const bare = verb.slice(cut + 1);
  const words = bare.replace(/[._]+/g, " ").trim();
  if (!words) return verb;
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/**
 * Akis satirinin `title` (tooltip) bilgisi: etiketli fiilde "etiket · ham
 * anahtar", etiketsizde yalnizca ham anahtar.
 * NEDEN: cumle insan diline cevrilir, ama hata ayiklarken "bu hangi kanonik
 * fiil?" sorusunun yaniti gorunur kalmali; ham anahtar yalnizca burada yasar.
 */
export function verbTitle(verb: string): string {
  const label = VERB_LABELS[verb];
  return label ? `${label} · ${verb}` : verb;
}

export function describe(verb: string, payload: Record<string, unknown>): string {
  const label = VERB_LABELS[verb] ?? readableFallback(verb);
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
