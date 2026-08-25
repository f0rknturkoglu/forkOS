import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw, Trash2 } from "lucide-react";
import { api } from "@/core/api";
import {Button, Chip, Empty, MiniStat, Section, cx, relativeTime, useToast} from "@/core/ui";
import { confirmDialog } from "@/core/dialog";
import { useInvalidate, useOnline } from "@/lib/hooks";
import type { Feed, RssStats } from "@/core/types";

function problemBadges(feed: Feed): { label: string; tone: "warn" | "danger" }[] {
  const badges: { label: string; tone: "warn" | "danger" }[] = [];
  if (feed.error_count > 0) badges.push({ label: `${feed.error_count} hata`, tone: "danger" });
  if (!feed.active) badges.push({ label: "kapatıldı", tone: "danger" });
  if (feed.last_status === "empty") badges.push({ label: "boş döndü", tone: "warn" });
  if (!feed.last_fetched_at) badges.push({ label: "çekilmedi", tone: "warn" });
  return badges;
}

/** RSS feed sagligi: sorunlu/kapatilmis/hic cekilmemis beslemeler + aksiyonlar. */
export function RssHealthWidget() {
  const online = useOnline();
  const invalidate = useInvalidate();
  const toast = useToast();

  const { data: feeds = [] } = useQuery({
    queryKey: ["feeds"],
    queryFn: () => api.get<Feed[]>("/rss/feeds"),
  });
  const { data: stats } = useQuery({
    queryKey: ["rss-stats"],
    queryFn: () => api.get<RssStats>("/rss/stats"),
  });

  // Sorunlu feed'ler: hata, kapatilmis, bos donmus ya da hic cekilmemis.
  const problems = feeds.filter((f) => problemBadges(f).length > 0);

  const refreshAll = useMutation({
    mutationFn: () => api.post<{ started: number }>("/rss/refresh-all"),
    onSuccess: (result) => {
      invalidate("feeds", "rss-stats");
      toast.push(
        result.started > 0
          ? `${result.started} besleme çekiliyor…`
          : "Süresi gelen besleme yok — hepsi taze.",
        { tone: result.started > 0 ? "neutral" : "ok" },
      );
    },
  });
  const refreshOne = useMutation({
    mutationFn: (id: string) => api.post(`/rss/feeds/${id}/refresh`),
    onSuccess: () => invalidate("feeds", "rss-stats", "items", "activity"),
  });
  // "Cevap vermeyen" feed'ler: hata biriktirmis ya da kapatilmis.
  const dead = feeds.filter((f) => f.error_count > 0 || !f.active);
  const deleteDead = useMutation({
    mutationFn: async () => {
      let removed = 0;
      for (const feed of dead) {
        try {
          await api.del(`/rss/feeds/${feed.id}`);
          removed += 1;
        } catch {
          // tek tek devam et; sonucta kullanici toplami gorur
        }
      }
      return removed;
    },
    onSuccess: (removed) => {
      invalidate("feeds", "items", "rss-stats", "activity");
      toast.push(
        removed > 0
          ? removed + " yanıt vermeyen besleme silindi."
          : "Silinecek besleme yok.",
        { tone: removed > 0 ? "ok" : "neutral" },
      );
    },
    onError: (error: Error) => toast.push("Silme başarısız: " + error.message, { tone: "danger" }),
  });

  async function confirmDeleteDead() {
    if (dead.length === 0) {
      toast.push("Yanıt vermeyen besleme yok.", { tone: "neutral" });
      return;
    }
    const ok = await confirmDialog({
      title: "Yanıt vermeyen beslemeler silinsin mi?",
      body: (<><strong className="font-medium text-primary">{dead.length}</strong> besleme (hata biriktirmiş veya kapatılmış) ve bağlı yazıları listeden kalkar. Geri alınamaz.</>),
      confirmLabel: "Sil",
      tone: "danger",
    });
    if (ok) deleteDead.mutate();
  }
  

  return (
    <Section
      title="RSS Sağlığı"
      action={
        <div className="flex items-center gap-2">
          <Button size="sm" disabled={!online || deleteDead.isPending} onClick={confirmDeleteDead} title="Hata biriktiren veya kapatılmış beslemeleri sil">
            <Trash2 size={13} />
            {dead.length > 0 ? `${dead.length} sorunlu sil` : "Sorunlu yok"}
          </Button>
          <Button size="sm" disabled={!online || refreshAll.isPending} onClick={() => refreshAll.mutate()}>
            <RefreshCw size={13} className={refreshAll.isPending ? "animate-spin" : undefined} />
            Tümünü tazele
          </Button>
        </div>
      }
      bodyClassName="space-y-4"
    >
      <div className="grid grid-cols-4 gap-3">
        <MiniStat label="Besleme" value={stats?.feeds ?? 0} />
        <MiniStat label="Aktif" value={stats?.active_feeds ?? 0} tone="ok" />
        <MiniStat label="Sorunlu" value={stats?.failing_feeds ?? 0} tone="danger" />
        <MiniStat label="Okunmamış" value={stats?.unread ?? 0} />
      </div>

      {problems.length === 0 ? (
        <Empty>Bütün beslemeler sağlıklı — hata yok, hepsi çekilmiş.</Empty>
      ) : (
        <div>
          <p className="mb-2 text-meta text-secondary">
            <strong className="font-medium text-danger">{problems.length}</strong> besleme ilgi istiyor:
          </p>
          <ul className="space-y-1.5">
            {problems.slice(0, 10).map((feed) => (
              <li
                key={feed.id}
                className="flex items-center gap-2.5 border-b border-subtle px-1 py-2 last:border-b-0"
              >
                <AlertTriangle size={13} className="shrink-0 text-warn" />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="max-w-[260px] truncate text-body text-primary">{feed.title}</span>
                    {problemBadges(feed).map((b) => (
                      <Chip key={b.label} tone={b.tone}>{b.label}</Chip>
                    ))}
                  </div>
                  <p className="mt-0.5 text-meta text-muted">
                    {feed.last_fetched_at ? `son çekim ${relativeTime(feed.last_fetched_at)}` : "hiç çekilmedi"}
                  </p>
                </div>
                <Button
                  size="sm"
                  disabled={!online || refreshOne.isPending}
                  onClick={() => refreshOne.mutate(feed.id)}
                  title="Bu beslemeyi şimdi çek"
                >
                  <RefreshCw size={13} /> Çek
                </Button>
              </li>
            ))}
          </ul>
          {problems.length > 10 && (
            <p className="mt-2 text-meta text-muted">+{problems.length - 10} besleme daha — tümünü tazele ile düzeltebilirsin.</p>
          )}
        </div>
      )}
    </Section>
  );
}