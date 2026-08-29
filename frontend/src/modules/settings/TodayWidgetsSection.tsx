import { useState } from "react";
import { ArrowDown, ArrowUp, Eye, EyeOff, RotateCcw } from "lucide-react";
import {
  allTodayWidgetViewsIncludingHidden,
  resetTodayWidgetPrefs,
  setTodayWidgetHidden,
  setTodayWidgetOrder,
  type TodayWidgetView,
} from "@/core/registry";
import { Button, Section, cx } from "@/core/ui";

const SLOT_LABELS = { left: "Plan", center: "Akış", right: "Durum" } as const;

function readHidden(): Set<string> {
  return new Set<string>(JSON.parse(localStorage.getItem("lifeos.todayWidgetHidden") ?? "[]"));
}

/**
 * Bugun widget yonetimi (Faz 19): gizle/goster, yukari/asagi, varsayilana don.
 *
 * Siralama ve gizleme kullanici tercihidir; degisiklik localStorage'a ve
 * (onPersist uzerinden) backend `today.widget_order` / `today.widget_hidden`
 * ayarlarina yazilir. Bir widget'i gizlemek modul rotasini veya Command
 * Palette komutlarini kapatmaz; `modules.disabled` ayri kalir.
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
  const [hidden, setHidden] = useState<Set<string>>(readHidden);
  const order = views.map((view) => view.id);

  function commit(nextOrder: string[], nextHidden: string[]) {
    setTodayWidgetOrder(nextOrder);
    setTodayWidgetHidden(nextHidden);
    setHidden(new Set(nextHidden));
    onPersist(nextOrder, nextHidden);
    setVersion((value) => value + 1);
  }

  function move(id: string, delta: -1 | 1) {
    const index = order.indexOf(id);
    const target = index + delta;
    if (index < 0 || target < 0 || target >= order.length) return;
    const next = [...order];
    [next[index], next[target]] = [next[target], next[index]];
    commit(next, [...hidden]);
  }

  function toggle(id: string) {
    const nextHidden = hidden.has(id) ? [...hidden].filter((item) => item !== id) : [...hidden, id];
    commit(order, nextHidden);
  }

  function reset() {
    resetTodayWidgetPrefs();
    onPersist([], []);
    setVersion((value) => value + 1);
  }

  return (
    <Section title="Bugün widget'ları">
      <p className="mb-2 text-meta text-muted">
        Widget'ları gizle, sırala. Sıra ve görünürlük kalıcıdır; modül rotaları ve komutları bundan etkilenmez. Modül
        kapatılırsa o modülün bütün widget'ları da kapanır.
      </p>
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
                  aria-label={`${view.title} yukarı taşı`}
                >
                  <ArrowUp size={13} />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!online || isHidden || position < 0 || position >= order.length - 1}
                  onClick={() => move(view.id, 1)}
                  title="Aşağı taşı"
                  aria-label={`${view.title} aşağı taşı`}
                >
                  <ArrowDown size={13} />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!online}
                  onClick={() => toggle(view.id)}
                  title={isHidden ? "Göster" : "Gizle"}
                  aria-label={`${view.title} ${isHidden ? "göster" : "gizle"}`}
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
