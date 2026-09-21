import { useRef, useState } from "react";
import { useRssStats, useSourceHealth, useSystemStats } from "@/core/runtimeQueries";
import { AlertTriangle, Clock4, Cpu, HardDrive, MemoryStick, X } from "lucide-react";
import { dataState } from "@/core/DataState";
import { runStateView } from "@/core/sourceStatus";
import { Chip, Popover, cx } from "@/core/ui";
import type { ChipTone } from "@/core/ui";
import type { SystemStats } from "@/core/types";

type Tone = "ok" | "warn" | "danger" | "muted";

const DOT: Record<Tone, string> = {
  ok: "bg-ok",
  warn: "bg-warn",
  danger: "bg-danger",
  muted: "bg-icon",
};

/** Noktanin cevresindeki solgun halka -- yanan bir LED izlenimi verir. */
const RING: Record<Tone, string> = {
  ok: "ring-ok-border",
  warn: "ring-warn-border",
  danger: "ring-danger-border",
  muted: "ring-subtle",
};

/**
 * Kaynak esikleri. Disk icin %85 fazla alingandi -- dolu bir gelistirme
 * diski surekli amber yakiyordu; gercek risk %92'den sonra basliyor.
 */
const WARN = { cpu: 0.8, mem: 0.9, disk: 0.92 };
const CRIT = { cpu: 0.95, mem: 0.97, disk: 0.97 };

function pct(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value * 100)));
}

function fmtUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d} g ${h} sa`;
  if (h > 0) return `${h} sa ${m} dk`;
  return `${m} dk`;
}

function Bar({
  label,
  value,
  hint,
  icon,
  limit,
}: {
  label: string;
  value: number | null;
  hint?: string;
  icon: React.ReactNode;
  /** Cubuk rengi LED ile ayni esikten okur; ikisi ayri konusmasin. */
  limit?: { warn: number; crit: number };
}) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between gap-2 text-meta">
        <span className="flex items-center gap-1.5 text-secondary">
          {icon} {label}
        </span>
        <span className="numeral text-primary">{value === null ? "ölçülüyor…" : `%${pct(value)}`}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-surface-sunken">
        <div
          className={cx(
            "h-full rounded-full transition-all",
            value === null
              ? "bg-icon"
              : value > (limit?.crit ?? 0.95)
                ? "bg-danger"
                : value > (limit?.warn ?? 0.85)
                  ? "bg-warn"
                  : "bg-ok",
          )}
          style={{ width: value === null ? "0%" : `${pct(value)}%` }}
        />
      </div>
      {hint && <p className="mt-1 text-micro leading-4 text-muted">{hint}</p>}
    </div>
  );
}

/** Panel satiri: renk tek basina anlam tasimaz, chip metni de durumu yazar. */
function StatusRow({ label, text, tone }: { label: string; text: string; tone: ChipTone }) {
  return (
    <li className="flex items-center justify-between gap-2">
      <span className="text-meta text-secondary">{label}</span>
      <Chip size="xs" tone={tone}>
        {text}
      </Chip>
    </li>
  );
}

/** Worker durumu (kaynak: /system/stats). `disabled` bir hata DEGILDIR. */
function workerView(worker: SystemStats["worker"] | undefined): { text: string; tone: ChipTone } {
  if (!worker || worker.status === "unknown") return { text: "bilinmiyor", tone: "neutral" };
  if (worker.status === "disabled") return { text: "kapalı", tone: "neutral" };
  if (worker.status === "stale") return { text: "bayat", tone: "warn" };
  return { text: "sağlıklı", tone: "ok" };
}

/**
 * Ust seritteki durum isigi.
 *
 * Isigin RENGI sunucunun kendi durumu: yesil = yerel API ayakta ve donanimda
 * sikisma yok, amber/kirmizi = gercekten sikisma var. Kirik kaynak ve
 * besleme sayilari PANELDE gorunur ama isigi boyamaz -- onlarin kendi uyari
 * seridi ve bildirim rozeti var, surekli sari yanan bir isik bir sure sonra
 * hic bakilmayan bir isik oluyor.
 *
 * Panel DURUSTTUR: bir sorgu dusmus ya da hala yukleniyorsa o satir
 * "bilinmiyor" der; hicbir kosulda "her sey saglikli" cumlesi kurulmaz.
 */
export function StatusLed() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const statsQuery = useSystemStats();
  const sourcesQuery = useSourceHealth();
  const rssQuery = useRssStats();
  const data = statsQuery.data;
  const { isError } = statsQuery;

  const memUsed = data?.mem_total_kb ? 1 - (data.mem_available_kb ?? 0) / data.mem_total_kb : null;
  const diskUsed = data?.disk ? 1 - data.disk.free / data.disk.total : null;
  const cpuUsed = data?.cpu_pct === null || data?.cpu_pct === undefined ? null : data.cpu_pct / 100;

  // Ilgi isteyen kosular: hata/kismi/yarim kaldi. `empty` ve `disabled` DEGIL.
  const sourceAttention = (sourcesQuery.data ?? []).filter((run) => runStateView(run.status).attention).length;
  const sourceState = dataState(sourcesQuery);
  const rssState = dataState(rssQuery);
  const failingFeeds = rssQuery.data?.failing_feeds ?? 0;

  const apiView: { text: string; tone: ChipTone } =
    dataState(statsQuery) === "ready" ? { text: "sağlıklı", tone: "ok" } : { text: "bilinmiyor", tone: "neutral" };
  const sourcesView: { text: string; tone: ChipTone } =
    sourceState === "ready"
      ? sourceAttention > 0
        ? { text: `${sourceAttention} ilgi istiyor`, tone: "warn" }
        : { text: "sorun yok", tone: "ok" }
      : sourceState === "empty"
        ? { text: "kayıt yok", tone: "neutral" }
        : { text: "bilinmiyor", tone: "neutral" };
  const rssView: { text: string; tone: ChipTone } =
    rssState === "ready"
      ? failingFeeds > 0
        ? { text: `${failingFeeds} sorunlu`, tone: "warn" }
        : { text: "sağlıklı", tone: "ok" }
      : { text: "bilinmiyor", tone: "neutral" };

  const over = (value: number | null, limit: number) => value !== null && value > limit;
  const tone: Tone = isError
    ? "danger"
    : !data
      ? "muted"
      : over(cpuUsed, CRIT.cpu) || over(memUsed, CRIT.mem) || over(diskUsed, CRIT.disk)
        ? "danger"
        : over(cpuUsed, WARN.cpu) || over(memUsed, WARN.mem) || over(diskUsed, WARN.disk)
          ? "warn"
          : "ok";

  const label = isError
    ? "sunucuya ulaşılamıyor"
    : tone === "ok"
      ? "yerel sunucu çalışıyor"
      : tone === "muted"
        ? "durum okunuyor"
        : "sunucu sıkışıyor";

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        title={`Sistem durumu — ${label}`}
        aria-label={`Sistem durumu — ${label}`}
        aria-expanded={open}
        className="flex h-8 w-8 items-center justify-center text-muted transition-colors hover:text-primary"
      >
        <span className={cx("h-2 w-2 rounded-full ring-4 transition-colors", DOT[tone], RING[tone])} />
      </button>

      <Popover
        open={open}
        onClose={() => setOpen(false)}
        anchorRef={rootRef}
        role="dialog"
        ariaLabel="Sistem durumu"
        className="right-0 top-full mt-2 w-72"
      >
        <div className="flex items-center justify-between gap-3 border-b border-subtle px-4 py-2.5">
          <span className="text-heading text-primary">Durum</span>
          <button
            type="button"
            onClick={() => setOpen(false)}
            title="Kapat"
            aria-label="Kapat"
            className="text-muted transition hover:text-primary"
          >
            <X size={14} />
          </button>
        </div>

        <div className="space-y-2 border-b border-subtle px-4 py-3">
          {isError && (
            <p className="flex items-center gap-2 text-body text-danger">
              <AlertTriangle size={15} aria-hidden className="shrink-0" /> Yerel API'ye ulaşılamıyor.
            </p>
          )}
          <ul className="space-y-1.5">
            <StatusRow label="Yerel API" {...apiView} />
            <StatusRow label="Kaynaklar" {...sourcesView} />
            <StatusRow label="RSS" {...rssView} />
            <StatusRow label="Worker" {...workerView(data?.worker)} />
          </ul>
          <a href="#/health" className="inline-block text-meta text-accent hover:underline">
            Sağlık paneli →
          </a>
        </div>

        {data && (
          <div className="space-y-3 px-4 py-3">
            <Bar
              label="CPU"
              value={cpuUsed}
              limit={{ warn: WARN.cpu, crit: CRIT.cpu }}
              hint={data.load.length > 0 ? `yük ${data.load[0].toFixed(2)} · ${data.cpu_count} çekirdek` : undefined}
              icon={<Cpu size={13} />}
            />
            <Bar
              label="RAM"
              value={memUsed}
              limit={{ warn: WARN.mem, crit: CRIT.mem }}
              icon={<MemoryStick size={13} />}
            />
            <Bar
              label="Disk"
              value={diskUsed}
              limit={{ warn: WARN.disk, crit: CRIT.disk }}
              hint={data.disk ? `${(data.disk.free / 1e9).toFixed(0)} GB boş · ${data.disk.path ?? "/app"}` : undefined}
              icon={<HardDrive size={13} />}
            />
            <p className="flex items-center gap-1.5 pt-1 text-meta text-muted">
              <Clock4 size={12} /> Makine {fmtUptime(data.uptime_s)} açık
            </p>
          </div>
        )}
      </Popover>
    </div>
  );
}
