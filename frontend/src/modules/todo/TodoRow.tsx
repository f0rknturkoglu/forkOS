import { invalidateAfter } from "@/core/invalidation";
import type { ReactNode } from "react";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Check, CornerDownRight, FolderGit2, ListTree, Milestone as MilestoneIcon, Repeat, Timer, Trash2, X,
} from "lucide-react";
import { api } from "@/core/api";
import {Chip, IconButton, Input, cx, useToast} from "@/core/ui";
import {useOnline} from "@/lib/hooks";
import { navigate } from "@/app/router";
import type { Todo } from "@/core/types";
import { dueLabel, priorityOf, recurLabel } from "./priority";

const DUE_CHIP = {
  muted: "border-subtle text-secondary",
  accent: "border-accent-border bg-accent-surface text-accent",
  danger: "border-danger-border bg-danger-surface text-danger",
} as const;

/** Proje rozetinin gittigi adres -- secili proje acilsin diye focus tasinir. */
const projectHref = (todo: Todo) =>
  todo.project_id ? `#/projects?focus=${encodeURIComponent(todo.project_id)}` : "#/projects";

/**
 * Tek gorev satiri. Hem Gorevler sayfasi hem Bugun paneli bunu kullanir --
 * tamamlama davranisi iki yerde ayrisirsa biri her zaman geride kaliyor.
 */
export function TodoRow({
  todo, compact = false, nested = false, onChange, children,
}: {
  todo: Todo;
  /** Bugun panelinde: baslik ve eylemler daha dar. */
  compact?: boolean;
  /** Alt gorev olarak, ust gorevin altinda girintili gosteriliyor. */
  nested?: boolean;
  onChange?: () => void;
  /** Alt gorev satirlari -- ayni bilesenin `nested` hali. */
  children?: ReactNode;
}) {
  const [editing, setEditing] = useState(false);
  const [subtask, setSubtask] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
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
    onSuccess: () => { refresh(); toast.push("Görev silindi", { tone: "ok" }); },
  });
  const addSubtask = useMutation({
    mutationFn: (title: string) =>
      api.post("/todos", {
        title,
        parent_id: todo.id,
        // Alt gorev ustunun onceligini ve kilometre tasini devralir --
        // ayri ayri secmek zorunda kalmayasin.
        priority: todo.priority,
        milestone_id: todo.milestone_id ?? undefined,
      }),
    onSuccess: () => { setSubtask(""); refresh(); },
  });

  const done = todo.status === "done";
  const dropped = todo.status === "dropped";
  const priority = priorityOf(todo.priority);
  const due = dueLabel(todo.due_at);
  const recur = recurLabel(todo.recur);

  // Pomodoro sayfasi context/topic parametrelerini acilis aninda okur --
  // "odaklan" bu adrese gidip formu doldurur, kullanici baslat der.
  const focusHref = `#/pomodoro?context=${encodeURIComponent(todo.id)}&topic=${encodeURIComponent(todo.title)}`;

  return (
    <li className={cx("group", nested && "pl-6")}>
     <div className={cx("flex items-start gap-2.5", compact ? "py-1.5" : "py-2.5")}>
      {nested && (
        <CornerDownRight size={13} className="mt-1 shrink-0 text-icon" aria-hidden />
      )}
      <button
        type="button"
        disabled={!online || done}
        onClick={() => complete.mutate()}
        aria-label={done ? "Tamamlandı" : "Tamamla"}
        title={done ? "Tamamlandı" : "Tamamla"}
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
            <Input autoFocus value={draft} onChange={setDraft} ariaLabel="Görev başlığı"
              onKeyDown={(event) => { if (event.key === "Escape") setEditing(false); }}
              className="min-w-0 flex-1" />
          </form>
        ) : (
          <button
            type="button"
            disabled={!online}
            onClick={() => { setDraft(todo.title); setEditing(true); }}
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
          * Meta satiri: her parca kendi hafif cercevesi icinde. Duz metin
          * yan yana dizilince "yuksek 23 Ağu her gün #ev" tek bir bulanik
          * satira donuyordu; elips/cerceve okunurlugu geri veriyor.
          */}
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-meta">
          {todo.priority > 0 && (
            <Chip tone={priority.tone} icon={<span className={cx("h-1.5 w-1.5 rounded-full", priority.dot)} />}>
              {priority.label}
            </Chip>
          )}
          {due && (
            <span className={cx(
              "rounded-full border px-2 py-0.5 text-micro leading-4",
              DUE_CHIP[due.tone],
            )}>
              {due.text}
            </span>
          )}
          {recur && todo.recur && (
            <span className="flex items-center gap-1 rounded-full border border-subtle px-2 py-0.5 text-micro leading-4 text-muted">
              <Repeat size={10} /> {recur}
            </span>
          )}
          {todo.project_title && (
            <a
              href={projectHref(todo)}
              title={`${todo.project_title} projesi`}
              className="flex items-center gap-1 rounded-full border border-accent-border bg-accent-surface px-2 py-0.5 text-micro leading-4 text-accent transition hover:brightness-95"
            >
              <FolderGit2 size={10} /> {todo.project_title}
            </a>
          )}
          {todo.milestone_title && (
            <a href={projectHref(todo)} title={`${todo.milestone_title} kilometre taşı`}>
              <Chip icon={<MilestoneIcon size={10} />}>{todo.milestone_title}</Chip>
            </a>
          )}
          {todo.subtask_total > 0 && (
            <span className="flex items-center gap-1 rounded-full border border-subtle px-2 py-0.5 text-micro leading-4 text-muted">
              <ListTree size={10} /> {todo.subtask_done}/{todo.subtask_total}
            </span>
          )}
          {todo.tags.map((tag) => (
            <span key={tag}
              className="rounded-full border border-subtle px-2 py-0.5 text-micro leading-4 text-secondary">
              #{tag}
            </span>
          ))}
          {dropped && (
            <span className="rounded-full border border-subtle px-2 py-0.5 text-micro leading-4 text-muted">
              bırakıldı
            </span>
          )}
        </div>
      </div>

      <div className={cx(
        "flex shrink-0 items-center gap-1 transition",
        "opacity-0 focus-within:opacity-100 group-hover:opacity-100",
      )}>
        {!done && !dropped && !nested && (
          <IconButton title="Alt görev ekle" disabled={!online}
            onClick={() => setSubtask((current) => (current === null ? "" : null))}>
            <ListTree size={14} />
          </IconButton>
        )}
        {!done && !dropped && (
          <IconButton title="Odaklan — pomodoro başlat" disabled={!online}
            onClick={() => navigate(focusHref)}>
            <Timer size={14} />
          </IconButton>
        )}
        {!done && !dropped && !compact && (
          <IconButton title="Bırak" disabled={!online}
            onClick={() => patch.mutate({ status: "dropped" })}>
            <X size={14} />
          </IconButton>
        )}
        <IconButton title="Sil" tone="danger" disabled={!online || remove.isPending}
          onClick={() => remove.mutate()}>
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
            onKeyDown={(event) => { if (event.key === "Escape") setSubtask(null); }}
            placeholder="Alt görev — Esc ile kapat"
            ariaLabel="Alt görev başlığı"
            className="min-w-0 flex-1"
          />
        </form>
      )}
    </li>
  );
}
