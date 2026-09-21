/**
 * Sistem Durumu — kanonik teşhis sayfası (§28/§67/§86).
 *
 * Üç anlamsal grup vardır ve her grup KENDİ sorgu hatasını taşır: bir tanılama
 * düşse bile sayfanın geri kalanı ayakta kalır.
 *
 *   1. Genel bakış      — API/runtime, worker, kaynak özeti, zihin katmanı, yedek
 *   2. İlgi gerekenler  — yalnız gösterilecek bir şey varsa; yoksa tek sakin satır
 *   3. Ayrıntılı sağlık — kaynak/RSS/yedek/servis kartları (2 sütun)
 *
 * Özetin kendisi (`SystemStatus.tsx`) ile paylaşılır: Ayarlar → Durum &
 * Kaynaklar sekmesi AYNI bileşenleri kullanır; burada yalnız ayrıntılı
 * kartlar ve kurulum kontrol listesi eklenir.
 *
 * Dürüstlük sözleşmesi ve sorgu sözleşmesi için bkz. `SystemStatus.tsx`.
 */
import { CopyButton, PageFrame, SectionHeader } from "@/core/ui";
import { Workspace, WorkspacePaneHeader, WorkspaceScrollArea } from "@/core/workspace/Workspace";
import { SetupChecklist } from "./SetupChecklist";
import { SystemStatusAttention, SystemStatusOverview, useHealthSummary } from "./SystemStatus";
import { DETAIL_WIDGETS } from "./widgets";

/* ── Sayfa ────────────────────────────────────────────────────────────── */

export function HealthPage() {
  const summary = useHealthSummary();

  return (
    <PageFrame>
      <Workspace>
        <WorkspacePaneHeader
          eyebrow="Sistem"
          title="Sistem Durumu"
          hint="Kaynaklar, beslemeler, yedekler ve ajan bağlantısı"
          action={
            <CopyButton
              text={summary.bundle}
              label="Teşhisi kopyala"
              ariaLabel="Agent için durum paketini kopyala"
              disabled={summary.loading}
              toastLabel="Sistem teşhisi panoya kopyalandı."
            />
          }
        />
        <WorkspaceScrollArea className="p-3">
          <div className="space-y-6">
            <SetupChecklist />
            <SystemStatusOverview summary={summary} />
            <SystemStatusAttention summary={summary} />
            <div>
              <SectionHeader label="Ayrıntılı sağlık" hint="kaynaklar · beslemeler · yedek · servis" />
              <div className="grid items-start gap-4 xl:grid-cols-2">
                {DETAIL_WIDGETS.map(({ name, component: Widget }) => (
                  <Widget key={name} />
                ))}
              </div>
            </div>
          </div>
        </WorkspaceScrollArea>
      </Workspace>
    </PageFrame>
  );
}
