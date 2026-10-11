import {
  Flame,
  Github,
  BookOpen,
  MessageSquare,
  Rss,
  Target,
  CalendarRange,
  GraduationCap,
  Compass,
} from "lucide-react";
import { enabledModules } from "@/core/registry";
import type { FeedOrigin } from "@/core/feedStream";

export const SOURCE_CATALOG = [
  {
    id: "hn",
    title: "Hacker News",
    description: "Teknoloji ve geliştirici gündemi",
    detail: "Algolia front page · makaleler ve tartışmalar",
    icon: Flame,
    skin: "text-feed-hn",
  },
  {
    id: "gh",
    title: "GitHub · Yeni ve Popüler",
    description: "Yeni açık kaynak projeleri",
    detail: "Son 7 günde açılan depolar · yıldız sırası",
    icon: Github,
    skin: "text-feed-gh",
  },
  {
    id: "hf",
    title: "Hugging Face Papers",
    description: "Günün araştırma seçkisi",
    detail: "Gerçek makale tarihi · yazarlar ve özet",
    icon: BookOpen,
    skin: "text-accent",
  },
  {
    id: "rss",
    title: "Kendi RSS kaynakların",
    description: "Takip ettiğin bloglar ve siteler",
    detail: "RSS adresi veya OPML · mevcut abonelikler korunur",
    icon: Rss,
    skin: "text-feed-rss",
  },
  {
    id: "reddit",
    title: "Reddit",
    description: "Seçtiğin topluluklar",
    detail: "Subreddit'leri sen seçersin",
    icon: MessageSquare,
    skin: "text-feed-reddit",
  },
] as const;
export const sourceInfo = (id: FeedOrigin) => SOURCE_CATALOG.find((source) => source.id === id)!;
export const PRESET_BUNDLES = [
  { title: "Yapay Zekâ & Araştırma", channels: ["hf", "hn"] as FeedOrigin[] },
  { title: "Yazılım & Açık Kaynak", channels: ["gh", "hn"] as FeedOrigin[] },
  { title: "Kendi Kaynaklarım", channels: ["rss"] as FeedOrigin[] },
];
export const JOURNEYS = [
  { id: "goal", title: "Hedeflerimi planlamak", module: "goal", icon: Target },
  { id: "planning", title: "Günümü düzenlemek", module: "todo", icon: CalendarRange },
  { id: "learning", title: "Öğrenmeye başlamak", module: "learning", icon: GraduationCap },
  { id: "career", title: "Kariyerimi yönetmek", module: "opportunity", icon: Compass },
] as const;
export interface TourStep {
  id: string;
  module: string;
  routeIndex?: number;
  params?: Record<string, string>;
  search?: Record<string, string>;
  target: string;
  title: string;
  text: string;
  actionType?: string;
}
const steps: TourStep[] = [
  {
    id: "home",
    module: "today",
    target: "workspace",
    title: "Bugünün çalışma alanı",
    text: "Planın, sıradaki işin ve bekleyen kararların burada.",
  },
  {
    id: "goal",
    module: "goal",
    search: { view: "objectives" },
    target: "goal-create",
    title: "Bir yön belirle",
    text: "Bir hedef oluştur veya mevcut hedefini aç. İlerlemeni ölçülebilir sonuçlarla izle.",
    actionType: "goal",
  },
  {
    id: "goal-milestone",
    module: "goal",
    search: { view: "objectives" },
    target: "goal-milestone",
    title: "Hedefi adımlara ayır",
    text: "Mevcut hedefini aç ve gerçek bir adım ekle. Adım tamamlamak ile sonucu ölçmek ayrı işlerdir.",
  },
  {
    id: "goal-keyresults",
    module: "goal",
    search: { view: "objectives" },
    target: "goal-keyresults",
    title: "Sonucu ölç",
    text: "Hedefinde KR ekle ile başlangıç, hedef ve güncel değerini tanımla.",
  },
  {
    id: "planning",
    module: "todo",
    target: "todo-create",
    title: "İlk işini yaz",
    text: "Gerçek bir görev ekle. Plan günü ile son tarih ayrı seçimlerdir.",
    actionType: "todo",
  },
  {
    id: "planner",
    module: "todo",
    routeIndex: 1,
    target: "workspace",
    title: "Haftana yerleştir",
    text: "Mevcut görevlerini haftalık plana al; saat ve süreyi buradan ayarla.",
  },
  {
    id: "projects",
    module: "projects",
    target: "project-create",
    title: "Projeye dön",
    text: "Bir proje aç; sıradaki adımını, işlerini ve geçmişini birlikte gör.",
    actionType: "project",
  },
  {
    id: "learning",
    module: "learning",
    target: "learning-create",
    title: "Öğrenme alanını kur",
    text: "Bir alan ve konu oluştur veya mevcut konuyu aç; kaynağını konuya bağla.",
    actionType: "study_topic",
  },
  {
    id: "learning-resource",
    module: "learning",
    target: "learning-resource",
    title: "Kaynağını konuya bağla",
    text: "Bir konuyu aç ve Kaynak ekle ile gerçek bir bağlantı, not veya kayıtlı makale bağla.",
  },
  {
    id: "flashcard",
    module: "flashcard",
    target: "workspace",
    title: "Kartlarını tekrar et",
    text: "Kart desteleri buradadır. Konu tekrarları öğrenme alanında, soru-cevap tekrarları kartlarda ilerler.",
  },
  {
    id: "learning-review",
    module: "learning",
    search: { view: "review" },
    target: "learning-review",
    title: "Tekrarla",
    text: "Konu tekrarları ve kart tekrarları iki ayrı öğrenme akışıdır.",
  },
  {
    id: "career",
    module: "opportunity",
    target: "workspace",
    title: "Kariyer çalışma alanı",
    text: "İlanı keşfetmek ile başvuru kaydı ayrı durumlardır. Bir fırsatı incele veya Kariyer Profili'ni aç.",
    actionType: "opportunity",
  },
  {
    id: "career-profile",
    module: "opportunity",
    search: { tab: "career" },
    target: "workspace",
    title: "Kariyer profilini tamamla",
    text: "Hedef rolünü, becerilerini ve CV bilgilerini kendi kayıtlarınla düzenle.",
  },
  {
    id: "career-applications",
    module: "opportunity",
    search: { tab: "applications" },
    target: "workspace",
    title: "Başvurunu izle",
    text: "Kısa liste başvuru değildir. Gönderdiğin gerçek başvuruyu, aşamasını ve sonraki adımını burada kaydet.",
  },
  {
    id: "feed",
    module: "rss",
    target: "feed-sources",
    title: "Akışını oluştur",
    text: "Kaynaklar + ile takip edeceklerini seç. Kaydetmeden hiçbir kaynak eklenmez.",
  },
  {
    id: "rss",
    module: "rss",
    routeIndex: 1,
    target: "workspace",
    title: "RSS kaynakların",
    text: "RSS adresi ekle veya mevcut OPML dosyanı içe aktar.",
  },
  {
    id: "bookmarks",
    module: "bookmarks",
    target: "workspace",
    title: "Sonra okumak için kaydet",
    text: "Kaydettiğin içerikleri okuyucuda aç; bir pasajı karta veya konu kaynağına dönüştür.",
  },
  {
    id: "review",
    module: "review",
    params: { kind: "weekly" },
    target: "workspace",
    title: "Haftayı değerlendir",
    text: "Kayıtlı ilerlemeyi gör, değerlendirmeyi kaydet ve açık işlerini gelecek haftaya taşı.",
  },
  {
    id: "setup",
    module: "settings",
    target: "workspace",
    title: "Kurulum ve bağlantılar",
    text: "İsteğe bağlı bağlantılar ve sistem kontrolleri Ayarlar'da. Temel kullanım için Hermes veya Obsidian gerekmez.",
  },
];
export const TOUR_IDS = [
  "general",
  "goal",
  "planning",
  "projects",
  "learning",
  "career",
  "feed",
  "rss",
  "bookmarks",
  "review",
  "setup",
];
export function tourSteps(id: string) {
  const ids =
    id === "general"
      ? ["home", "goal", "planning", "projects", "learning", "career", "feed", "review"]
      : id === "goal"
        ? ["goal", "goal-milestone", "goal-keyresults"]
        : id === "career"
          ? ["career", "career-profile", "career-applications"]
          : id === "planning"
            ? ["planning", "planner", "home"]
            : id === "learning"
              ? ["learning", "learning-resource", "learning-review", "flashcard", "bookmarks"]
              : id === "feed"
                ? ["feed", "rss", "bookmarks"]
                : [id];
  return ids
    .flatMap((id) => steps.filter((step) => step.id === id))
    .flatMap((step) => {
      const module = enabledModules().find((module) => module.id === step.module);
      const route = module?.routes[step.routeIndex ?? 0];
      if (!route) return [];
      let path = route.path;
      for (const [param, value] of Object.entries(step.params ?? {})) path = path.replace(":" + param, value);
      if (path.includes(":")) return [];
      if (step.search) path += "?" + new URLSearchParams(step.search).toString();
      return [{ ...step, path, moduleTitle: module!.title }];
    });
}
export function helpForModule(id: string) {
  return steps.filter((step) => step.module === id);
}
