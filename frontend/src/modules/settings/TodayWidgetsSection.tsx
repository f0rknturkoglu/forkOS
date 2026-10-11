import { ArrowDown, ArrowUp, Eye, EyeOff, RotateCcw } from "lucide-react";
import {
  allTodayWidgetViews,
  allTodayWidgetViewsIncludingHidden,
  resetTodayWidgetPrefs,
  setTodayWidgetHidden,
  setTodayWidgetOrder,
  useTodayWidgetViewsIncludingHidden,
} from "@/core/registry";
import type { TodayWidgetView } from "@/core/registry";
import { focusedConfig, overviewConfig, PRESET_LABELS } from "@/core/todayPresets";
import type { TodayPreset } from "@/core/todayPresets";
import { Button, Section, cx } from "@/core/ui";
import type { TodayPlacement } from "@/core/types";

/** Çekirdek yüzeyin nerede durduğu: kullanıcı iskeleti buradan okur. */
const PLACEMENT_LABELS: Record<TodayPlacement, string> = {
  now: "Şimdi",
  plan: "Günün planı",
  attention: "Dikkat",
  context: "Bağlam",
};

/**
 * Mevcut ETKIN durumu acik tercihe cevirir: gorunur istege bagli yuzeyler sira,
 * gorunmeyenler gizli listesine. Cekirdek yuzeyler yazilmaz -- gizlenemezler.
 */
function currentConfig(): { order: string[]; hidden: string[] } {
  const optional = allTodayWidgetViewsIncludingHidden().filter((view) => !view.widget.core);
  const visible = new Set(allTodayWidgetViews().map((view) => view.id));
  return {
    order: optional.filter((view) => visible.has(view.id)).map((view) => view.id),
    hidden: optional.filter((view) => !visible.has(view.id)).map((view) => view.id),
  };
}

/**
 * Home widget yonetimi (Faz 19/20): İSTEĞE BAĞLI yüzeyleri gizle/göster ve
 * sırala. Çekirdek yüzeyler iskeleti kurar: listede görünürler ama
 * gizlenemez/sıralanamazlar (§17). Değişiklik localStorage + backend
 * `today.widget_order` / `today.widget_hidden` ayarlarına yazılır; Home aynı
 * oturumda yenilenir (registry reaktif store yayınlar).
 *
 * Widget gizlemek modül rotasını veya Command Palette komutlarını kapatmaz;
 * `modules.disabled` ayrı kalır.
 */
export function TodayWidgetsSection({
  online,
  onPersist,
}: {
  online: boolean;
  onPersist: (order: string[], hidden: string[]) => void;
}) {
  const views: TodayWidgetView[] = useTodayWidgetViewsIncludingHidden();
  const config = currentConfig();
  const hidden = new Set(config.hidden);
  const order = config.order;

  const coreViews = views.filter((view) => view.widget.core);
  const optionalViews = views.filter((view) => !view.widget.core);
  const zoneOf = (id: string) => optionalViews.find((view) => view.id === id)?.widget.placement ?? "context";
  const zoneOrder = (id: string) => order.filter((candidate) => zoneOf(candidate) === zoneOf(id));

  function commit(nextOrder: string[], nextHidden: string[]) {
    setTodayWidgetOrder(nextOrder);
    setTodayWidgetHidden(nextHidden);
    onPersist(nextOrder, nextHidden);
  }

  function move(id: string, delta: -1 | 1) {
    const base = currentConfig();
    const withinZone = base.order.filter((candidate) => zoneOf(candidate) === zoneOf(id));
    const index = withinZone.indexOf(id);
    const target = index + delta;
    if (index < 0 || target < 0 || target >= withinZone.length) return;
    const next = [...base.order];
    const other = withinZone[target];
    const otherIndex = next.indexOf(other);
    const ownIndex = next.indexOf(id);
    [next[ownIndex], next[otherIndex]] = [next[otherIndex], next[ownIndex]];
    commit(next, base.hidden);
  }

  function toggle(id: string) {
    const base = currentConfig();
    const isHidden = base.hidden.includes(id);
    const nextHidden = isHidden ? base.hidden.filter((item) => item !== id) : [...base.hidden, id];
    const nextOrder = isHidden ? [...base.order, id] : base.order;
    commit(nextOrder, nextHidden);
  }

  function reset() {
    resetTodayWidgetPrefs();
    onPersist([], []);
  }

  function applyPreset(preset: TodayPreset) {
    const config = preset === "focused" ? focusedConfig() : overviewConfig();
    commit(config.order, config.hidden);
  }

  return (
    <Section title="Home bileşenleri">
      <p className="mb-2 text-meta text-muted">
        Çekirdek yüzeyler Home iskeletini kurar; her zaman görünürler. İsteğe bağlı yüzeyleri gizleyip kendi bölgesinde
        sıralayabilirsin. Sıra ve görünürlük kalıcıdır; modül rotaları ve komutları bundan etkilenmez.
      </p>
      <div className="mb-3 flex items-center gap-2">
        <span className="text-meta text-muted">Hazır düzen:</span>
        {(["focused", "overview"] as TodayPreset[]).map((preset) => (
          <Button
            key={preset}
            size="sm"
            variant={preset === "focused" ? "primary" : "ghost"}
            disabled={!online}
            onClick={() => applyPreset(preset)}
          >
            {PRESET_LABELS[preset]}
          </Button>
        ))}
      </div>

      <ul className="stack-divide-y divide-subtle rounded-card border border-subtle">
        {coreViews.map((view) => (
          <li key={view.id} className="flex items-center gap-2 px-3 py-2">
            <div className="min-w-0 flex-1">
              <p className="truncate text-body text-primary">{view.title}</p>
              <p className="text-meta text-muted">
                {view.moduleId} · {PLACEMENT_LABELS[view.widget.core ?? "context"]} · çekirdek
              </p>
            </div>
          </li>
        ))}
      </ul>

      <p className="mb-2 mt-4 text-meta text-muted">İsteğe bağlı yüzeyler</p>
      <ul className="stack-divide-y divide-subtle rounded-card border border-subtle">
        {optionalViews.map((view) => {
          const isHidden = hidden.has(view.id);
          const group = zoneOrder(view.id);
          const groupPosition = group.indexOf(view.id);
          return (
            <li key={view.id} className="flex items-center gap-2 px-3 py-2">
              <div className="min-w-0 flex-1">
                <p className={cx("truncate text-body", isHidden ? "text-muted line-through" : "text-primary")}>
                  {view.title}
                </p>
                <p className="text-meta text-muted">
                  {view.moduleId} · {PLACEMENT_LABELS[view.widget.placement ?? "context"]}
                  {isHidden && " · gizli"}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!online || isHidden || groupPosition <= 0}
                  onClick={() => move(view.id, -1)}
                  title="Yukarı taşı"
                  ariaLabel={`${view.title} yukarı taşı`}
                >
                  <ArrowUp size={13} />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!online || isHidden || groupPosition < 0 || groupPosition >= group.length - 1}
                  onClick={() => move(view.id, 1)}
                  title="Aşağı taşı"
                  ariaLabel={`${view.title} aşağı taşı`}
                >
                  <ArrowDown size={13} />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!online}
                  onClick={() => toggle(view.id)}
                  title={isHidden ? "Göster" : "Gizle"}
                  ariaLabel={`${view.title} ${isHidden ? "göster" : "gizle"}`}
                >
                  {isHidden ? <Eye size={13} /> : <EyeOff size={13} />}
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
      <div className="mt-2">
        <Button size="sm" variant="ghost" disabled={!online} onClick={reset} title="Varsayılana dön">
          <RotateCcw size={13} /> Varsayılana dön
        </Button>
      </div>
    </Section>
  );
}
