import { useState } from "react";
import { ArrowDown, ArrowUp, Eye, EyeOff, RotateCcw } from "lucide-react";
import {
  allTodayWidgetViews,
  allTodayWidgetViewsIncludingHidden,
  resetTodayWidgetPrefs,
  setTodayWidgetHidden,
  setTodayWidgetOrder,
  type TodayWidgetView,
} from "@/core/registry";
import { focusedConfig, overviewConfig, PRESET_LABELS, type TodayPreset } from "@/core/todayPresets";
import { Button, Section, cx } from "@/core/ui";

const SLOT_LABELS = { left: "Plan", center: "Akış", right: "Durum" } as const;

/**
 * Mevcut ETKIN durumu acik tercihe cevirir: gorunur widget'lar sira,
 * gorunmeyenler (varsayilan-gizli + kullanici-gizli) gizli listesine.
 * Ilk etkilesimde varsayilan odakli duzen bozulmaz (Faz 20).
 */
function currentConfig(): { order: string[]; hidden: string[] } {
  const visible = allTodayWidgetViews();
  const all = allTodayWidgetViewsIncludingHidden();
  const visibleIds = new Set(visible.map((view) => view.id));
  return {
    order: visible.map((view) => view.id),
    hidden: all.filter((view) => !visibleIds.has(view.id)).map((view) => view.id),
  };
}

/**
 * Bugun widget yonetimi (Faz 19/20): gizle/goster, yukari/asagi, preset,
 * varsayilana don. Degisiklik localStorage + backend `today.widget_order` /
 * `today.widget_hidden` ayarlarina yazilir. Widget gizlemek modul rotasini
 * veya Command Palette komutlarini kapatmaz; `modules.disabled` ayri kalir.
 */
export function TodayWidgetsSection({
  online,
  onPersist,
}: {
  online: boolean;
  onPersist: (order: string[], hidden: string[]) => void;
}) {
  const [version, setVersion] = useState(0);
  const views: TodayWidgetView[] = allTodayWidgetViewsIncludingHidden();
  const config = currentConfig();
  const hidden = new Set(config.hidden);
  const order = config.order;

  function commit(nextOrder: string[], nextHidden: string[]) {
    setTodayWidgetOrder(nextOrder);
    setTodayWidgetHidden(nextHidden);
    onPersist(nextOrder, nextHidden);
    setVersion((value) => value + 1);
  }

  function move(id: string, delta: -1 | 1) {
    const base = currentConfig();
    const index = base.order.indexOf(id);
    const target = index + delta;
    if (index < 0 || target < 0 || target >= base.order.length) return;
    const next = [...base.order];
    [next[index], next[target]] = [next[target], next[index]];
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
    setVersion((value) => value + 1);
  }

  function applyPreset(preset: TodayPreset) {
    const config = preset === "focused" ? focusedConfig() : overviewConfig();
    commit(config.order, config.hidden);
  }

  return (
    <Section title="Home bileşenleri">
      <p className="mb-2 text-meta text-muted">
        Widget'ları gizle, sırala. Sıra ve görünürlük kalıcıdır; modül rotaları ve komutları bundan etkilenmez. Modül
        kapatılırsa o modülün bütün widget'ları da kapanır.
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
      <ul className="divide-y divide-subtle rounded-card border border-subtle">
        {views.map((view) => {
          const isHidden = hidden.has(view.id);
          const position = order.indexOf(view.id);
          return (
            <li key={view.id} className="flex items-center gap-2 px-3 py-2">
              <div className="min-w-0 flex-1">
                <p className={cx("truncate text-body", isHidden ? "text-muted line-through" : "text-primary")}>
                  {view.title}
                </p>
                <p className="text-meta text-muted">
                  {view.moduleId} · {SLOT_LABELS[view.widget.slot ?? "center"]} · #{view.widget.order}
                  {isHidden && " · gizli"}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!online || isHidden || position <= 0}
                  onClick={() => move(view.id, -1)}
                  title="Yukarı taşı"
                  ariaLabel={`${view.title} yukarı taşı`}
                >
                  <ArrowUp size={13} />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!online || isHidden || position < 0 || position >= order.length - 1}
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
        <span className="ml-2 text-meta text-muted">{version > 0 ? "Kaydedildi." : ""}</span>
      </div>
    </Section>
  );
}
