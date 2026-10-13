import { invalidateAfter } from "@/core/invalidation";
import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Calendar,
  CalendarPlus,
  Check,
  CornerDownRight,
  FolderGit2,
  ListTree,
  Milestone as MilestoneIcon,
  Repeat,
  Timer,
  Trash2,
  X,
} from "lucide-react";
import { api } from "@/core/api";
import { createTask } from "@/core/tasks";
import { IconButton, Input, cx, useToast } from "@/core/ui";
import { useOnline } from "@/lib/hooks";
import { openPomodoro } from "@/modules/pomodoro/dock";
import type { Todo } from "@/core/types";
import { appLocalToUtc, todayKey } from "@/lib/date";
import { RECURRENCES, dueLabel, planLabel, priorityOf, recurLabel } from "./priority";

/** Son tarih tonlari: cerceve yok, yalniz metin rengi. */
const DUE_TEXT = {
  muted: "text-muted",
  accent: "text-accent",
  danger: "text-danger",
} as const;

/** Plan tonlari: gelecek plan bilgi, gecikmis plan uyari. */
const PLAN_TEXT = {
  muted: "text-muted",
  accent: "text-accent",
  warn: "text-warn",
} as const;

/** Proje rozetinin gittigi adres -- secili proje acilsin diye focus tasinir. */
const projectHref = (todo: Todo) =>
  todo.project_id ? `#/projects?focus=${encodeURIComponent(todo.project_id)}` : "#/projects";

/**
 * Tek gorev satiri. Hem Gorevler sayfasi hem Bugun paneli bunu kullanir --
 * tamamlama davranisi iki yerde ayrisirsa biri her zaman geride kaliyor.
 */
export function TodoRow({
  todo,
  compact = false,
  nested = false,
  focused = false,
  onChange,
  children,
}: {
  todo: Todo;
  /** Bugun panelinde: baslik ve eylemler daha dar. */
  compact?: boolean;
  /** Alt gorev olarak, ust gorevin altinda girintili gosteriliyor. */
  nested?: boolean;
  /** ?focus= rotasindan acilan hedef satir. */
  focused?: boolean;
  onChange?: () => void;
  /** Alt gorev satirlari -- ayni bilesenin `nested` hali. */
  children?: ReactNode;
}) {
  const [editing, setEditing] = useState(false);
  const [subtask, setSubtask] = useState<string | null>(null);
  const [editingRecur, setEditingRecur] = useState(false);
  const [draft, setDraft] = useState("");
  const rowRef = useRef<HTMLLIElement>(null);
  const online = useOnline();
  const toast = useToast();

  const refresh = () => {
    invalidateAfter("todo.write");
    onChange?.();
  };

  const complete = useMutation({
    mutationFn: () => api.post(`/todos/${todo.id}/complete`),
    onSuccess: refresh,
  });
  const patch = useMutation({
    mutationFn: (body: object) => api.patch(`/todos/${todo.id}`, body),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => api.del(`/todos/${todo.id}`),
    onSuccess: () => {
      refresh();
      toast.push("Görev silindi", { tone: "ok" });
    },
  });
  const addSubtask = useMutation({
    mutationFn: (title: string) =>
      createTask({
        title,
        parent_id: todo.id,
        // Alt gorev ustunun onceligini ve kilometre tasini devralir --
        // ayri ayri secmek zorunda kalmayasin.
        priority: todo.priority,
        milestone_id: todo.milestone_id ?? undefined,
      }),
    onSuccess: () => {
      setSubtask("");
      refresh();
    },
  });

  const done = todo.status === "done";
  const dropped = todo.status === "dropped";
  const priority = priorityOf(todo.priority);
  const due = dueLabel(todo.due_at);
  const recur = recurLabel(todo.recur);
  const plan = planLabel(todo.planned_day ?? null, todo.planned_start_min ?? null);

  /**
   * Satir meta parcalari sirayla: oncelik (varsayilan disiysa), son tarih,
   * plan, rutin, proje, kilometre tasi, alt gorev sayaci, etiketler.
   * Kaynak bilgisi (ogrenme konusu) YAZILMAZ: basligin kendisi konu agacina
   * bagli, ikinci bir rozet ayni seyi tekrar ediyordu.
   */
  const meta: { key: string; node: ReactNode }[] = [];
  if (todo.priority !== 2) {
    meta.push({
      key: "priority",
      node: (
        <span className={cx("flex items-center gap-1", priority.text)}>
          <span className={cx("h-1.5 w-1.5 rounded-full", priority.dot)} />
          {priority.label}
        </span>
      ),
    });
  }
  if (due) {
    meta.push({
      key: "due",
      node: <span className={DUE_TEXT[due.tone]}>{due.text}</span>,
    });
  }
  if (plan) {
    meta.push({
      key: "plan",
      node: (
        <span title="Plana alındı — son tarih değil" className={cx("flex items-center gap-1", PLAN_TEXT[plan.tone])}>
          <Calendar size={11} /> {plan.text}
        </span>
      ),
    });
  }
  if (recur && todo.recur) {
    meta.push({
      key: "recur",
      node: (
        <button
          type="button"
          title={
            todo.due_at
              ? `Rutin — sonraki: ${dueLabel(todo.due_at)?.text ?? ""} (düzenlemek için tıkla)`
              : "Rutin — sonraki tarih yok (düzenlemek için tıkla)"
          }
          onClick={() => setEditingRecur((value) => !value)}
          className="flex items-center gap-1 text-muted transition hover:text-primary"
        >
          <Repeat size={11} /> {recur}
        </button>
      ),
    });
  }
  if (todo.project_title) {
    meta.push({
      key: "project",
      node: (
        <a
          href={projectHref(todo)}
          title={`${todo.project_title} projesi`}
          className="flex items-center gap-1 text-accent hover:underline"
        >
          <FolderGit2 size={11} /> {todo.project_title}
        </a>
      ),
    });
  }
  if (todo.milestone_title) {
    meta.push({
      key: "milestone",
      node: (
        <a
          href={projectHref(todo)}
          title={`${todo.milestone_title} kilometre taşı`}
          className="flex items-center gap-1 text-secondary hover:text-primary"
        >
          <MilestoneIcon size={11} /> {todo.milestone_title}
        </a>
      ),
    });
  }
  if (todo.subtask_total > 0) {
    meta.push({
      key: "subtasks",
      node: (
        <span className="flex items-center gap-1 text-muted">
          <ListTree size={11} /> {todo.subtask_done}/{todo.subtask_total}
        </span>
      ),
    });
  }
  todo.tags.forEach((tag) => {
    meta.push({
      key: `tag:${tag}`,
      node: <span className="text-secondary">#{tag}</span>,
    });
  });
  if (dropped) {
    meta.push({ key: "dropped", node: <span className="text-muted">bırakıldı</span> });
  }

  useEffect(() => {
    if (focused) rowRef.current?.scrollIntoView({ block: "center" });
  }, [focused]);

  return (
    <li
      ref={rowRef}
      data-focused={focused || undefined}
      className={cx(
        "group scroll-mt-24",
        // Odak karti (bg + ring) satirin KENDI kutusudur; yatay dolgu olmadan
        // soldaki tamamlama dairesi ile sagdaki aksiyonlar yuvarlak koseden
        // tasip cerceveyi deliyordu. Ic ice satirlar zaten 24px girintili.
        nested ? "pl-6 pr-3" : "px-3",
        focused && "rounded-control bg-accent-surface ring-1 ring-inset ring-accent",
      )}
    >
      <div className={cx("flex items-start gap-2.5", compact ? "py-1.5" : "py-2.5")}>
        {nested && <CornerDownRight size={13} className="mt-1 shrink-0 text-icon" aria-hidden />}
        <button
          type="button"
          disabled={!online || complete.isPending || patch.isPending}
          onClick={() => (done ? patch.mutate({ status: "open" }) : complete.mutate())}
          aria-label={done ? "Yeniden aç" : "Tamamla"}
          title={done ? "Tamamlandı — yeniden aç" : "Tamamla"}
          className={cx(
            "mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border transition",
            done
              ? "border-ok bg-ok text-canvas"
              : "border-strong text-transparent hover:border-accent hover:text-accent",
            !online && "cursor-not-allowed opacity-50",
          )}
        >
          <Check size={12} strokeWidth={3} />
        </button>

        <div className="min-w-0 flex-1">
          {editing ? (
            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                const value = draft.trim();
                setEditing(false);
                if (value && value !== todo.title) patch.mutate({ title: value });
              }}
            >
              <Input
                autoFocus
                value={draft}
                onChange={setDraft}
                ariaLabel="Görev başlığı"
                onKeyDown={(event) => {
                  if (event.key === "Escape") setEditing(false);
                }}
                className="min-w-0 flex-1"
              />
            </form>
          ) : todo.learning_topic_id ? (
            <a
              href={`#/learning?focus=${encodeURIComponent(todo.learning_topic_id)}`}
              title={`${todo.learning_topic_title ?? todo.title} konu ağacını aç`}
              className={cx(
                "block w-full truncate text-left text-body transition",
                done || dropped ? "text-muted line-through" : "text-primary hover:text-accent hover:underline",
              )}
            >
              {todo.title}
            </a>
          ) : (
            <button
              type="button"
              disabled={!online}
              onClick={() => {
                setDraft(todo.title);
                setEditing(true);
              }}
              title="Başlığı düzenle"
              className={cx(
                "block w-full truncate text-left text-body transition",
                done || dropped ? "text-muted line-through" : "text-primary hover:text-accent",
              )}
            >
              {todo.title}
            </button>
          )}

          {/*
           * Meta satiri duz metin: her parca kendi cercevesi icinde olunca
           * satir rozet yiginina donuyordu. Ayrac + ton rengi okunurlugu
           * cercevesiz koruyor; varsayilan oncelik ("orta") hic yazilmaz,
           * cunku her satirda tekrar eden bilgi degil gurultu.
           */}
          {meta.length > 0 && (
            <div className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-meta">
              {meta.map((item, index) => (
                <span key={item.key} className="flex items-center gap-1.5">
                  {index > 0 && (
                    <span aria-hidden className="text-icon">
                      ·
                    </span>
                  )}
                  {item.node}
                </span>
              ))}
            </div>
          )}

          {editingRecur && todo.recur && (
            <span className="mt-1 flex flex-wrap items-center gap-1">
              {RECURRENCES.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  aria-pressed={todo.recur === item.value}
                  onClick={() => {
                    patch.mutate(
                      { recur: item.value },
                      {
                        onSuccess: () =>
                          toast.push(
                            item.value === ""
                              ? "Rutin durduruldu — bu görev duruyor."
                              : `Rutin güncellendi: ${item.label}`,
                            { tone: "ok" },
                          ),
                        onError: () => toast.push("Rutin güncellenemedi.", { tone: "danger" }),
                      },
                    );
                    setEditingRecur(false);
                  }}
                  className={cx(
                    "rounded-control border px-2 py-0.5 text-micro transition",
                    todo.recur === item.value
                      ? "border-accent-border bg-accent-surface text-accent"
                      : "border-subtle text-muted hover:border-strong",
                  )}
                >
                  {item.label}
                </button>
              ))}
            </span>
          )}
        </div>

        <div
          className={cx(
            "flex shrink-0 items-center gap-1 transition",
            "opacity-0 focus-within:opacity-100 group-hover:opacity-100",
          )}
        >
          {!done && !dropped && !nested && (
            <IconButton
              title="Alt görev ekle"
              disabled={!online}
              onClick={() => setSubtask((current) => (current === null ? "" : null))}
            >
              <ListTree size={14} />
            </IconButton>
          )}
          {!done && !dropped && (
            <IconButton
              title="Odaklan — pomodoro seçeneklerini aç"
              disabled={!online}
              onClick={() => openPomodoro({ context: todo.id, topic: todo.title })}
            >
              <Timer size={14} />
            </IconButton>
          )}
          {!done && !dropped && !compact && !todo.due_at && (
            <IconButton
              title="Son tarih ver (bugün) — plan değil"
              disabled={!online}
              onClick={() => {
                // App gununun ogleni (Faz 14/34): tarayicinin yerel saati
                // degil; app tz wall time -> ISO UTC donusumu appLocalToUtc.
                patch.mutate({ due_at: appLocalToUtc(todayKey(), 12, 0) });
              }}
            >
              <CalendarPlus size={14} />
            </IconButton>
          )}
          {!done && !dropped && !compact && (
            <IconButton title="Bırak" disabled={!online} onClick={() => patch.mutate({ status: "dropped" })}>
              <X size={14} />
            </IconButton>
          )}
          <IconButton title="Sil" tone="danger" disabled={!online || remove.isPending} onClick={() => remove.mutate()}>
            <Trash2 size={14} />
          </IconButton>
        </div>
      </div>

      {children && <ul className="border-t border-subtle">{children}</ul>}

      {subtask !== null && (
        <form
          className="mb-2 flex items-center gap-2 pl-7"
          onSubmit={(event) => {
            event.preventDefault();
            const value = subtask.trim();
            if (value) addSubtask.mutate(value);
          }}
        >
          <CornerDownRight size={13} className="shrink-0 text-icon" aria-hidden />
          <Input
            autoFocus
            value={subtask}
            onChange={setSubtask}
            onKeyDown={(event) => {
              if (event.key === "Escape") setSubtask(null);
            }}
            placeholder="Alt görev — Esc ile kapat"
            ariaLabel="Alt görev başlığı"
            className="min-w-0 flex-1"
          />
        </form>
      )}
    </li>
  );
}
