/**
 * Ortak gorev olusturma sozlesmesi (Faz 17).
 *
 * Butun manuel task girisleri (TodoComposer, todo.quick, DropCapture,
 * alt gorev, ProjectTodos, Learning, Opportunity...) `createTask` ile
 * POST /todos yapar; daginik body uretimi yasaktir (koruyan test
 * `taskCreation.test.ts`).
 *
 * "Bugune al" tercihi burada yasar: `plan_day` uretir, ASLA `due_at`
 * uretmez (Faz 13/17). Otomatik rutin occurrence'lari bu katmandan
 * gecmez -- `_spawn_next_occurrence` kullanici istemedikce plan yazmaz.
 */
import { invalidateAfter } from "@/core/invalidation";
import { api } from "@/core/api";
import { localDateKey } from "@/lib/date";
import type { Todo } from "@/core/types";

export interface TaskIntent {
  title: string;
  description?: string;
  priority?: number;
  due_at?: string;
  /** Açıkça verilirse tercihten önce gelir; verilmezse kayıtlı tercih uygulanır. */
  plan_day?: string;
  recur?: string;
  tags?: string[];
  parent_id?: string;
  project_id?: string;
  milestone_id?: string;
}

// Faz 13'te TodoComposer'da yasayan tercih; ortak capture katmanina tasindi.
export const PLAN_KEY = "todo.planToday";

export function readPlanTodayPreference(): boolean {
  return typeof localStorage !== "undefined" && localStorage.getItem(PLAN_KEY) === "1";
}

export function writePlanTodayPreference(checked: boolean): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(PLAN_KEY, checked ? "1" : "0");
}

/** "Bugune al" aciksa bugunun app gun anahtari; degilse undefined. */
export function planDayForToday(): string | undefined {
  return readPlanTodayPreference() ? localDateKey(new Date()) : undefined;
}

/** Tek POST /todos noktasi: intent'i güvenli body'ye cevirir. */
export async function createTask(intent: TaskIntent): Promise<Todo> {
  const planDay = intent.plan_day ?? planDayForToday();
  return api.post<Todo>("/todos", {
    title: intent.title.trim(),
    priority: intent.priority ?? 2,
    ...(intent.description ? { description: intent.description } : {}),
    ...(intent.due_at ? { due_at: intent.due_at } : {}),
    ...(intent.recur ? { recur: intent.recur } : {}),
    ...(intent.tags && intent.tags.length > 0 ? { tags: intent.tags } : {}),
    ...(intent.parent_id ? { parent_id: intent.parent_id } : {}),
    ...(intent.project_id ? { project_id: intent.project_id } : {}),
    ...(intent.milestone_id ? { milestone_id: intent.milestone_id } : {}),
    // "Bugune al" yalnizca plan_day uretir (Faz 13); due_at dokunulmaz.
    ...(planDay ? { plan_day: planDay } : {}),
  });
}

/** Gorev yazma invalidation'i: plan_day ihtimaline karsi plan.write da. */
export function invalidateTaskWrite(): void {
  invalidateAfter("todo.write", "plan.write");
}
