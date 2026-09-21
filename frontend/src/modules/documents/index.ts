/**
 * Belgeler (Drive) — ÜRÜN YÜZEYİ DEĞİL.
 *
 * Drive belgeleri kendi başına bir modül değildir: CV ve gereksinim dosyaları
 * fırsat/başvuru bağlamında yaşar, yükleme ve Drive senkronu arka planda
 * çalışmaya devam eder. Bu yüzden sidebar satırı, Home widget'ı ve komutu
 * KALDIRILDI; rota eski bağlantılar (ör. fırsat ekranındaki belge bağlantısı,
 * `/documents?focus=<id>`) kırılmasın diye gizli olarak durur.
 *
 * Belge domain'i (tablo, uçlar, yerel depolama, kariyer ilişkileri) korunur.
 */
import { lazy } from "react";
import { FileText } from "lucide-react";
import { registerModule } from "@/core/registry";

const DocumentsPage = lazy(() => import("./DocumentsPage").then((module) => ({ default: module.DocumentsPage })));

registerModule({
  id: "documents",
  title: "Belgeler",
  description: "Drive belgelerini ara, önizle ve son açılanlara hızlıca dön.",
  icon: FileText,
  routes: [{ path: "/documents", element: DocumentsPage, navigation: "hidden" }],
});
