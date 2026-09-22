/**
 * Ürün navigasyonu: modül envanteri değil, ürün ALANLARI.
 *
 * Sidebar'ın tek kaynağı burasıdır. Modül registry'si teknik kayıt defteridir
 * (rota, widget, komut, entité tipi); kullanıcı navigasyonu ondan TÜREMEZ.
 * Bir modül çalışıyor olabilir ama birincil sidebar'da satır tutmayabilir:
 *
 *   inbox     triyaj akışıdır; girişi Home'daki gelen kutusu yüzeyidir
 *   health    sağlık ve kaynak operasyonları Ayarlar'ın altındadır
 *   sources   aynı sahiplik: rota durur, satır tutmaz
 *   documents Drive belgeleri kariyer bağlamında yaşar, ürün yüzeyi değildir
 *   media     Kütüphane altında bir satırdır, kendi başına birincil hedef değil
 *
 * Kural: rota → ürün alanı eşleşmesi BAŞKA HİÇBİR YERDE yazılmaz. Başlık ve
 * ikon için modül aramaya devam eden `moduleForPath` bundan ayrıdır; ikisi
 * farklı soruları yanıtlar.
 *
 * Alan satırları registry rotalarından türetilir:
 *   - modülün birincil rotası (child/hidden olmayan ilk statik rota) → modül satırı
 *   - `navigation: "child"` işaretli rotalar → modülün altında alt satır
 *   - `links` → rota tablosunda karşılığı olmayan alan-içi görünümler (ör. ?view=review)
 */
import { findRouteMatch } from "@/app/router";
import {
  Activity,
  CalendarRange,
  ClipboardCheck,
  Compass,
  GraduationCap,
  Home,
  Layers,
  Library,
  SlidersHorizontal,
  Wallet,
} from "lucide-react";
import type { ModuleSpec } from "./types";

/** Alanın sidebar'daki yeri: gövde (birincil) ya da alt bölüm (sistem). */
type NavigationPlacement = "primary" | "system";

export type ProductAreaId =
  "home" | "plan" | "projects" | "career" | "learning" | "library" | "finance" | "activity" | "review" | "system";

/** Bir alanın altındaki tek satır: mevcut bir rota ya da alan-içi derin görünüm. */
export interface NavigationRow {
  /** Satırın sahibi modül (modül sidebar'ı ve aktiflik için). */
  moduleId: string;
  path: string;
  label: string;
  icon?: ModuleSpec["icon"];
  /** Derin görünüm sorgusu; yalnız alan `links`'lerinde bulunur. */
  query?: string;
  /**
   * Ağaçtaki derinlik: 1 = alanın doğrudan hedefi (modül satırı),
   * 2 = o hedefin alt rotası (`/planner`, `/activity/heatmap`).
   * Sidebar yalnız görsel ağırlığı değiştirir; üst satır, alt rotalardan biri
   * aktifken kendini pasif gösterir: `/habits` açıkken "Görevler" vurgulu
   * kalmasın diye.
   */
  depth: 1 | 2;
}

export interface ProductArea {
  id: ProductAreaId;
  label: string;
  icon: ModuleSpec["icon"];
  placement: NavigationPlacement;
  /**
   * Alana ait modüller; SIRA satır sırasını belirler. Kayıtlı olmayan
   * (kapatılmış) modüller sessizce atlanır: kapatılan modül rotasını da
   * getirmez, satır da bırakmaz.
   */
  moduleIds: readonly string[];
  /** Etikete tıklamak buraya gider. Yoksa alan yalnızca katlanır/açılır. */
  landing?: string;
  /** Satır etiketi modül başlığından farklı olacaksa (ör. Sağlık → Sistem Durumu). */
  labels?: Readonly<Record<string, string>>;
  /** Registry'de rotası olmayan alan-içi görünümler. */
  links?: readonly { path: string; label: string; query?: string; icon?: ModuleSpec["icon"] }[];
}

/**
 * ÜRÜN HARİTASI. Buradaki sıra kullanıcının gördüğü sıradır.
 *
 * Uzun kuyruk YOK: Finans, Etkinlik ve Değerlendirme eskiden "Daha fazla"
 * başlığı altında saklanıyordu; kullanıcı bu kavramı okumak zorunda kalıyordu.
 * Artık hepsi sıradan birer hedef.
 *
 * Domain/backend modülleri burada birleştirilmez: Plan altındaki `todo`,
 * `calendar` ve `pomodoro` ayrı servisler olarak kalır; yalnız tek bir zihinsel
 * çalışma alanında sunulur.
 */
const PRODUCT_AREAS: readonly ProductArea[] = [
  {
    id: "home",
    label: "Home",
    icon: Home,
    placement: "primary",
    moduleIds: ["today"],
    landing: "/",
  },
  {
    id: "plan",
    label: "Plan",
    icon: CalendarRange,
    placement: "primary",
    moduleIds: ["todo", "calendar", "pomodoro"],
    landing: "/todos",
  },
  {
    id: "projects",
    label: "Projeler",
    icon: Layers,
    placement: "primary",
    moduleIds: ["projects"],
    landing: "/projects",
  },
  {
    id: "career",
    label: "Kariyer",
    icon: Compass,
    placement: "primary",
    moduleIds: ["opportunity"],
    landing: "/opportunities",
  },
  {
    id: "learning",
    label: "Öğrenme",
    icon: GraduationCap,
    placement: "primary",
    moduleIds: ["learning", "flashcard"],
    landing: "/learning",
    links: [{ path: "/learning", label: "Tekrar", query: "view=review" }],
  },
  {
    id: "library",
    label: "Kütüphane",
    icon: Library,
    placement: "primary",
    // Bilgi (Vault köprüsü) da kütüphanenin parçasıdır: kaydettiğin, okuduğun
    // ve bilgiye dönüştürdüğün içerik aynı zihinsel rafta durur. Belgeler
    // BURADA DEĞİL: Drive belgeleri kariyer/başvuru bağlamında yaşar, kendi
    // başına bir ürün yüzeyi değildir (rota compat için durur).
    moduleIds: ["bookmarks", "rss", "media", "knowledge"],
    landing: "/bookmarks",
  },
  {
    id: "finance",
    label: "Finans",
    icon: Wallet,
    placement: "primary",
    moduleIds: ["finance"],
    landing: "/finance",
  },
  {
    id: "activity",
    label: "Etkinlik",
    icon: Activity,
    placement: "primary",
    moduleIds: ["activity"],
    landing: "/activity",
    labels: { activity: "Etkinlik" },
  },
  {
    id: "review",
    label: "Değerlendirme",
    icon: ClipboardCheck,
    placement: "primary",
    moduleIds: ["review"],
    landing: "/review/weekly",
  },
  {
    id: "system",
    label: "Sistem",
    icon: SlidersHorizontal,
    placement: "system",
    // Sistem girişi TEK: Ayarlar. Kaynaklar ve Sistem Durumu kendi rotalarını
    // korur (bildirimler, eski bağlantılar) ama sidebar satırı tutmaz; sahibi
    // Ayarlar > Durum & Kaynaklar'dır. Rakip bir giriş noktası bırakılmaz.
    moduleIds: ["settings"],
  },
];

function isDynamic(path: string): boolean {
  return path.split("/").some((part) => part.startsWith(":"));
}

/** Modülün sidebar satırı olan rotası: child/hidden olmayan ilk statik rota. */
function primaryRoute(module: ModuleSpec) {
  return (
    module.routes.find(
      (route) => route.navigation !== "child" && route.navigation !== "hidden" && !isDynamic(route.path),
    ) ?? module.routes[0]
  );
}

function areaModules(area: ProductArea, modules: readonly ModuleSpec[]): ModuleSpec[] {
  return area.moduleIds.flatMap((id) => {
    const module = modules.find((candidate) => candidate.id === id);
    return module ? [module] : [];
  });
}

/** Alanın altındaki satırlar (modül sırası + modülün alt rota sırası). */
export function areaRows(area: ProductArea, modules: readonly ModuleSpec[]): NavigationRow[] {
  const rows: NavigationRow[] = [];
  for (const module of areaModules(area, modules)) {
    const primary = primaryRoute(module);
    if (primary) {
      rows.push({
        moduleId: module.id,
        path: primary.path,
        label: area.labels?.[module.id] ?? module.title,
        icon: module.icon,
        depth: 1,
      });
    }
    for (const route of module.routes) {
      if (route.navigation !== "child") continue;
      rows.push({
        moduleId: module.id,
        path: route.path,
        label: route.title ?? module.title,
        icon: route.icon,
        depth: 2,
      });
    }
  }
  for (const link of area.links ?? []) {
    rows.push({
      moduleId: area.moduleIds[0] ?? area.id,
      path: link.path,
      label: link.label,
      icon: link.icon ?? area.icon,
      query: link.query,
      depth: 1,
    });
  }
  return rows;
}

/**
 * Alanın sahip olduğu TÜM rotalar (aktiflik için). Gizli ve dinamik rotalar da
 * dahildir: `/statistics`, `/study`, `/media/stats` gibi yollar doğru alanı
 * işaretlemelidir.
 */
function areaRoutes(area: ProductArea, modules: readonly ModuleSpec[]): string[] {
  const paths = areaModules(area, modules).flatMap((module) => module.routes.map((route) => route.path));
  if (area.landing) paths.push(area.landing);
  for (const link of area.links ?? []) paths.push(link.path);
  return paths;
}

/** Path'in ait olduğu ürün alanı (tam eşleşme global olarak kazanır, derin alt rota öneki yedekler). */
export function areaForPath(path: string, modules: readonly ModuleSpec[]): ProductArea | undefined {
  const candidates = PRODUCT_AREAS.flatMap((area) => areaRoutes(area, modules).map((route) => ({ path: route, area })));
  const direct = findRouteMatch(candidates, path)?.area;
  if (direct) return direct;
  return candidates.find((c) => c.path !== "/" && path.startsWith(`${c.path}/`))?.area;
}

export function areasAt(placement: NavigationPlacement): ProductArea[] {
  return PRODUCT_AREAS.filter((area) => area.placement === placement);
}

/** Satır aktif mi: rota eşleşmesi (veya alt rota öneki) + varsa derin görünüm sorgusu. */
export function rowIsActive(row: NavigationRow, path: string, params: URLSearchParams): boolean {
  const matchesRoute =
    Boolean(findRouteMatch([{ path: row.path }], path)) || (row.path !== "/" && path.startsWith(`${row.path}/`));
  if (!matchesRoute) return false;
  if (!row.query) return true;
  for (const [key, value] of new URLSearchParams(row.query)) {
    if (params.get(key) !== value) return false;
  }
  return true;
}

/** Alanın kendi satırı aktif mi (alan içindeki herhangi bir rota veya alt rota). */
export function areaIsActive(area: ProductArea, path: string, modules: readonly ModuleSpec[]): boolean {
  const routes = areaRoutes(area, modules);
  if (
    findRouteMatch(
      routes.map((route) => ({ path: route })),
      path,
    )
  ) {
    return true;
  }
  return routes.some((route) => route !== "/" && path.startsWith(`${route}/`));
}

/** Bir modülün birincil rota yolu; sidebar dışı satırlar (ör. sabitlenmiş görünüm) için. */
export function moduleLanding(modules: readonly ModuleSpec[], moduleId: string): string | undefined {
  const module = modules.find((candidate) => candidate.id === moduleId);
  return module ? primaryRoute(module)?.path : undefined;
}

/**
 * Alanın sidebar satırı olarak nasıl çizileceği:
 *   "link"    → tek hedefi var (Home, Projeler); alt satır yok, satır hedefe gider
 *   "section" → hedefi var, altında satırlar var (Plan, Öğrenme, Kütüphane);
 *               satırın TAMAMI katlanır/açılır, ayrıca gezinmez
 */
export function areaShape(area: ProductArea, modules: readonly ModuleSpec[]): "link" | "section" {
  const rows = areaRows(area, modules);
  if (rows.length <= 1 && rows[0]?.path === area.landing) return "link";
  return "section";
}
