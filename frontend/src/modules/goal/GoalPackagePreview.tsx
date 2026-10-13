import { useRef, useState } from "react";
import { PRIORITIES } from "@/modules/todo/priority";
import { Button, Checkbox, Disclosure, Field, Input, NumberInput, Select, Textarea } from "@/core/ui";
import { appLocalToUtc, localDateKey } from "@/lib/date";
import { typeLabel } from "@/core/entityRegistry";
import type { components } from "@/generated/api-schema";

type Proposal = components["schemas"]["StudioProposal-Output"];
type Op = Proposal["operations"][number];
const sections: [string, string[]][] = [
  ["Hedef özeti", ["goal.create", "goal.update", "key_result.save"]],
  ["Yol haritası", ["roadmap.create", "roadmap.update", "milestone.create", "milestone.update"]],
  ["Oluşturulacak görevler", ["todo.create"]],
  ["Düzenlenecek görevler", ["todo.update"]],
  ["Takvim planı", ["plan.schedule"]],
  ["Öğrenme konuları ve kaynaklar", ["learning.area", "learning.topic", "learning.resource"]],
  ["Mevcut kayıtlara bağlantılar", ["record.link"]],
];

export function GoalPackagePreview({
  proposal: incoming,
  before,
  onChange: publish,
  disabled,
}: {
  proposal: Proposal;
  before: Record<string, unknown>;
  onChange: (next: Proposal) => void;
  disabled: boolean;
}) {
  const draft = useRef(incoming);
  const previousProp = useRef(incoming);
  if (previousProp.current !== incoming) {
    draft.current = incoming;
    previousProp.current = incoming;
  }
  const proposal = draft.current;
  const onChange = (next: Proposal) => {
    draft.current = next;
    publish(next);
  };
  const [newTitle, setNewTitle] = useState("");
  const [destination, setDestination] = useState("");
  const [newKind, setNewKind] = useState("task");
  const previous = (op: Op) =>
    "target_id" in op && op.target_id
      ? (
          before[op.target_id] as {
            record?: {
              description?: string | null;
              due_at?: string | null;
              target_at?: string | null;
              priority?: number;
              manual_value?: string | null;
            };
          }
        )?.record
      : undefined;
  const title = (op: Op) =>
    "title" in op.data && op.data.title
      ? op.data.title
      : "target_id" in op && op.target_id
        ? ((before[op.target_id] as { title?: string })?.title ?? "Mevcut kayıt")
        : "";
  const dateValue = (op: Op) => {
    const field = op.type.startsWith("goal.") ? "target_at" : "due_at";
    const data = op.data as { target_at?: string | null; due_at?: string | null };
    const value = field in data ? data[field] : previous(op)?.[field];
    return value ? localDateKey(new Date(value)) : "";
  };
  const refTitle = (ref: string) => {
    const op = proposal.operations.find((o) => o.key === ref);
    const record = before[ref] as { title?: string; type?: string } | undefined;
    return op ? title(op) : (record?.title ?? "Mevcut kayıt");
  };
  const change = (key: string, field: string, value: unknown) =>
    onChange({
      ...draft.current,
      operations: draft.current.operations.map((op) =>
        op.key === key || (field === "title" && op.type === "roadmap.create" && op.target_ref === key)
          ? ({
              ...op,
              data: {
                ...op.data,
                [field]: value,
                ...(op.type === "plan.schedule" && field === "day" ? { calendar_override: false } : {}),
              },
            } as Op)
          : op,
      ),
    });
  const remove = (key: string) => {
    const removed = new Set([key]);
    let added = true;
    while (added) {
      added = false;
      for (const op of proposal.operations) {
        if (removed.has(op.key)) {
          if (
            op.type === "roadmap.create" &&
            op.target_ref &&
            proposal.operations.some((o) => o.key === op.target_ref) &&
            !proposal.operations.some(
              (o) => o.type === "roadmap.create" && !removed.has(o.key) && o.target_ref === op.target_ref,
            )
          ) {
            if (!removed.has(op.target_ref)) {
              removed.add(op.target_ref);
              added = true;
            }
          }
          continue;
        }
        const refs = Object.entries(op)
          .filter(([name]) => name.endsWith("_ref"))
          .map(([, value]) => value);
        if (refs.some((ref) => typeof ref === "string" && removed.has(ref))) {
          removed.add(op.key);
          added = true;
        }
      }
    }
    const removedTargets = new Set(
      proposal.operations
        .filter((op) => removed.has(op.key) && op.type === "roadmap.create")
        .flatMap((op) => (op.type === "roadmap.create" && op.target_ref ? [op.target_ref] : [])),
    );
    const remaining = proposal.operations
      .filter((op) => !removed.has(op.key))
      .filter(
        (op) =>
          op.type !== "record.link" ||
          !removedTargets.has(op.from_ref) ||
          proposal.operations.some(
            (o) => o.type === "roadmap.create" && !removed.has(o.key) && o.target_ref === op.from_ref,
          ),
      )
      .map((op) =>
        op.type === "roadmap.create"
          ? { ...op, depends_on: (op.depends_on ?? []).filter((ref) => !removed.has(ref)) }
          : op,
      );
    onChange({
      ...proposal,
      operations: remaining.filter(
        (op) =>
          op.type !== "learning.area" || remaining.some((o) => o.type === "learning.topic" && o.area_ref === op.key),
      ),
    });
  };
  const phases = proposal.operations.filter(
    (op) => op.type === "roadmap.create" && ["phase", "period"].includes(op.data.kind),
  );
  const phaseOptions = [
    ...phases.map((op) => ({ key: op.key, label: title(op), goalRef: "goal_ref" in op ? op.goal_ref : "" })),
    ...Object.entries(before).flatMap(([id, value]) => {
      const row = value as { type?: string; title?: string; record?: { kind?: string; goal_id?: string } };
      return row.type === "goal_roadmap_node" &&
        ["phase", "period"].includes(row.record?.kind ?? "") &&
        row.record?.goal_id
        ? [{ key: id, label: row.title ?? "Mevcut aşama", goalRef: row.record.goal_id }]
        : [];
    }),
  ];
  return (
    <div className="stack-y-5" aria-label="Hedef paketi önizlemesi">
      {proposal.planning && (
        <Field label="Günlük çalışma kapasitesi (dakika)">
          <NumberInput
            ariaLabel="Paket günlük kapasitesi"
            value={proposal.planning.daily_capacity_min ?? 30}
            min={1}
            max={480}
            disabled={disabled}
            onChange={(v) =>
              onChange({
                ...proposal,
                planning: { ...proposal.planning!, daily_capacity_min: v, capacity_confirmed: true },
                assumptions: proposal.assumptions?.filter((a) => !a.startsWith("Başlangıç için günlük")),
              })
            }
          />
        </Field>
      )}
      {proposal.planning && (
        <Disclosure summary="Çalışma günleri ve uygun saatler">
          <div className="flex flex-wrap gap-3">
            {["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"].map((label, index) => {
              const days = proposal.planning!.weekdays ?? [0, 1, 2, 3, 4, 5, 6];
              return (
                <Checkbox
                  key={label}
                  label={label}
                  checked={days.includes(index)}
                  disabled={disabled || (days.length === 1 && days.includes(index))}
                  onChange={(checked) =>
                    onChange({
                      ...proposal,
                      planning: {
                        ...proposal.planning!,
                        weekdays: checked ? [...days, index].sort() : days.filter((i) => i !== index),
                      },
                    })
                  }
                />
              );
            })}
          </div>
          <div className="grid gap-2 sm:grid-cols-2 mt-3">
            {(["available_start_min", "available_end_min"] as const).map((field, index) => {
              const minute = proposal.planning![field];
              return (
                <Field key={field} label={index ? "Uygun saat bitişi" : "Uygun saat başlangıcı"}>
                  <Input
                    type="time"
                    ariaLabel={index ? "Paket uygun saat bitişi" : "Paket uygun saat başlangıcı"}
                    disabled={disabled}
                    value={
                      minute == null
                        ? ""
                        : `${String(Math.floor(minute / 60)).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`
                    }
                    onChange={(value) => {
                      const parts = value.split(":").map(Number);
                      onChange({
                        ...proposal,
                        planning: {
                          ...proposal.planning!,
                          [field]: value ? parts[0] * 60 + parts[1] : null,
                          capacity_confirmed: true,
                        },
                      });
                    }}
                  />
                </Field>
              );
            })}
          </div>
          <p className="text-meta text-muted mt-2">
            Saat aralığını boş bırakırsan çalışmalar gün düzeyinde planlanır. Değişen kapasiteye göre blokları
            düzenleyebilir veya Hermes’ten yeni plan isteyebilirsin.
          </p>
        </Disclosure>
      )}
      {sections.map(([heading, types]) => {
        // Leaf graph copies are shown next to the canonical work, not as repeated forms.
        const ops = proposal.operations.filter(
          (op) =>
            types.includes(op.type) &&
            !(op.type === "roadmap.create" && ["record", "milestone", "child_goal"].includes(op.data.kind)),
        );
        if (!ops.length) return null;
        return (
          <section key={heading} className="stack-y-2">
            <h4 className="text-heading font-semibold">{heading}</h4>
            {heading === "Takvim planı" && (
              <p className="text-meta text-secondary">Çalışma günlerini ve her bloğun süresini düzenleyebilirsin.</p>
            )}
            {ops.map((op) => (
              <div key={op.key} className="rounded-card border border-subtle bg-surface p-3 stack-y-2">
                {("title" in op.data || op.type === "todo.update") && (
                  <Field label={op.type === "key_result.save" ? "Gerçek sonuç" : "Adı"}>
                    <Input
                      ariaLabel={`${heading}: ${title(op)}`}
                      value={title(op)}
                      disabled={disabled}
                      onChange={(value) => change(op.key, "title", value)}
                    />
                  </Field>
                )}
                {("description" in op.data || op.type === "todo.update") && (
                  <Field label="Açıklama">
                    <Textarea
                      ariaLabel={`${title(op)} açıklama`}
                      value={"description" in op.data ? (op.data.description ?? "") : (previous(op)?.description ?? "")}
                      disabled={disabled}
                      rows={2}
                      onChange={(v) => change(op.key, "description", v || null)}
                    />
                  </Field>
                )}
                {op.type === "key_result.save" && (
                  <div className="grid gap-2 sm:grid-cols-2">
                    <Field label="Hedef değer">
                      <Input
                        type="number"
                        ariaLabel="Hedeflenen sonuç"
                        value={String(op.data.target_value)}
                        disabled={disabled}
                        onChange={(v) => change(op.key, "target_value", v)}
                      />
                    </Field>
                    <p className="text-meta text-muted self-center">
                      {op.data.unit} ·{" "}
                      {previous(op)?.manual_value == null
                        ? "Güncel ölçüm henüz bilinmiyor"
                        : `Son ölçüm: ${previous(op)!.manual_value} ${op.data.unit} · korunacak`}
                    </p>
                  </div>
                )}
                {(op.type === "goal.create" ||
                  op.type === "goal.update" ||
                  op.type === "todo.create" ||
                  op.type === "todo.update" ||
                  op.type === "milestone.create" ||
                  op.type === "milestone.update") && (
                  <Field
                    label={op.type.startsWith("todo.") ? "Teslim tarihi (isteğe bağlı)" : "Hedef tarihi (biliniyorsa)"}
                  >
                    <Input
                      type="date"
                      ariaLabel={`${title(op)} tarihi`}
                      onInput={(v) =>
                        change(
                          op.key,
                          op.type.startsWith("goal.") ? "target_at" : "due_at",
                          v ? appLocalToUtc(v, 0, 0) : null,
                        )
                      }
                      value={dateValue(op)}
                      disabled={disabled}
                      onChange={(v) =>
                        change(
                          op.key,
                          op.type.startsWith("goal.") ? "target_at" : "due_at",
                          v ? appLocalToUtc(v, 0, 0) : null,
                        )
                      }
                      onBlur={(v) => {
                        if (v !== dateValue(op))
                          change(
                            op.key,
                            op.type.startsWith("goal.") ? "target_at" : "due_at",
                            v ? appLocalToUtc(v, 0, 0) : null,
                          );
                      }}
                    />
                  </Field>
                )}
                {(op.type === "todo.create" || op.type === "todo.update") && (
                  <Field label="Öncelik">
                    <Select
                      ariaLabel={`${title(op)} öncelik`}
                      disabled={disabled}
                      value={String(op.data.priority ?? previous(op)?.priority ?? 2)}
                      onChange={(value) => change(op.key, "priority", Number(value))}
                    >
                      {PRIORITIES.map((priority) => (
                        <option key={priority.value} value={priority.value}>
                          {priority.label}
                        </option>
                      ))}
                    </Select>
                  </Field>
                )}
                {"goal_ref" in op && <p className="text-meta text-secondary">Hedef: {refTitle(op.goal_ref)}</p>}
                {op.type === "plan.schedule" && (
                  <>
                    <p className="text-body font-medium">{refTitle(op.task_ref)}</p>
                    <Field label="Başlangıç saati (isteğe bağlı)">
                      <Input
                        type="time"
                        ariaLabel={`${refTitle(op.task_ref)} başlangıç saati`}
                        disabled={disabled}
                        value={
                          op.data.start_min == null
                            ? ""
                            : `${String(Math.floor(op.data.start_min / 60)).padStart(2, "0")}:${String(op.data.start_min % 60).padStart(2, "0")}`
                        }
                        onChange={(value) => {
                          const parts = value.split(":").map(Number);
                          change(op.key, "start_min", value ? parts[0] * 60 + parts[1] : null);
                        }}
                      />
                    </Field>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <Field label="Çalışma günü">
                        <Input
                          type="date"
                          ariaLabel={`${refTitle(op.task_ref)} plan günü`}
                          onInput={(v) => change(op.key, "day", v)}
                          value={op.data.day}
                          disabled={disabled}
                          onChange={(v) => change(op.key, "day", v)}
                          onBlur={(v) => {
                            if (v !== op.data.day) change(op.key, "day", v);
                          }}
                        />
                      </Field>
                      <Field label="Dakika">
                        <NumberInput
                          ariaLabel={`${refTitle(op.task_ref)} dakika`}
                          value={op.data.duration_min ?? 30}
                          min={1}
                          max={480}
                          disabled={disabled}
                          onChange={(v) => change(op.key, "duration_min", v)}
                        />
                      </Field>
                    </div>
                    <p className="text-meta text-muted">
                      {op.data.start_min == null
                        ? "Gün düzeyinde plan · kesin saat rezervasyonu değil"
                        : `Başlangıç: ${Math.floor(op.data.start_min / 60)}:${String(op.data.start_min % 60).padStart(2, "0")}`}
                    </p>
                    <Checkbox
                      label={`${refTitle(op.task_ref)}: takvim engeline rağmen bu gün çalışmayı seçiyorum`}
                      checked={op.data.calendar_override ?? false}
                      disabled={disabled}
                      onChange={(value) => change(op.key, "calendar_override", value)}
                    />
                  </>
                )}
                {op.type === "record.link" && (
                  <p className="text-body">
                    {refTitle(op.from_ref)} → {refTitle(op.to_ref)}{" "}
                    <span className="text-meta text-muted">· Var olan kayıt onayla bağlanacak</span>
                  </p>
                )}
                {op.type === "roadmap.update" && op.detached && (
                  <p className="text-meta text-warn">
                    Bu adım ve alt dalları haritadan çıkarılacak; asıl kayıtlar korunacak.
                  </p>
                )}
                {op.type === "learning.topic" && (
                  <p className="text-meta text-secondary">
                    Öğrenme alanı: {refTitle(op.area_ref)}
                    {op.parent_ref ? ` · Üst konu: ${refTitle(op.parent_ref)}` : ""}
                  </p>
                )}
                {op.type === "todo.create" && op.topic_ref && (
                  <p className="text-meta text-secondary">Öğrenme çalışması: {refTitle(op.topic_ref)}</p>
                )}
                {op.type === "learning.resource" && (
                  <p className="text-meta text-muted">
                    Kaynak ihtiyacı · {op.data.note} · {refTitle(op.topic_ref)}
                  </p>
                )}
                {!op.type.startsWith("goal.") && op.type !== "key_result.save" && (
                  <Button size="sm" variant="ghost" disabled={disabled} onClick={() => remove(op.key)}>
                    Paketten çıkar
                  </Button>
                )}
              </div>
            ))}
          </section>
        );
      })}
      {[
        ...new Set(
          proposal.operations.flatMap((op) =>
            op.type === "learning.topic" && before[op.area_ref] ? [op.area_ref] : [],
          ),
        ),
      ].map((areaId) => (
        <section key={areaId} className="rounded-card border border-subtle p-3 stack-y-2">
          <p>Mevcut öğrenme alanı: {refTitle(areaId)}</p>
          <p className="text-meta text-muted">Yeni konular bu alana eklenecek.</p>
          <Button
            disabled={disabled}
            size="sm"
            onClick={() => {
              const key = "user_area_" + crypto.randomUUID().replaceAll("-", "").slice(0, 20);
              onChange({
                ...proposal,
                operations: [
                  { key, type: "learning.area", data: { title: refTitle(areaId).slice(0, 100) } },
                  ...proposal.operations.map((op) =>
                    op.type === "learning.topic" && op.area_ref === areaId ? { ...op, area_ref: key } : op,
                  ),
                ],
              });
            }}
          >
            Ayrı bir öğrenme alanı oluştur
          </Button>
        </section>
      ))}
      {proposal.operations
        .filter((op) => op.type === "roadmap.create" && op.target_ref && before[op.target_ref])
        .map((op) => {
          if (op.type !== "roadmap.create" || !op.target_ref) return null;
          const record = before[op.target_ref] as { title?: string; type?: string };
          return (
            <div key={op.key} className="rounded-card border border-subtle p-3">
              <p>
                {record.title} · {record.type ? typeLabel(record.type) : "Kayıt"}
              </p>
              <p className="text-meta text-muted">Yerel mevcut kayıt kullanılacak; yeni kopya oluşturulmayacak.</p>
              <Button disabled={disabled} size="sm" onClick={() => remove(op.key)}>
                Bu eşleşmeyi reddet
              </Button>
            </div>
          );
        })}
      {!disabled && (
        <section className="rounded-card border border-subtle p-3 stack-y-2">
          <h4 className="text-heading">Eksik bir adım ekle</h4>
          <Select ariaLabel="Yeni adım türü" value={newKind} onChange={setNewKind}>
            <option value="task">Görev</option>
            <option value="topic">Öğrenme konusu</option>
            <option value="phase">Aşama</option>
          </Select>
          <Input ariaLabel="Yeni adım başlığı" value={newTitle} onChange={setNewTitle} placeholder="Ne yapılmalı?" />
          {newKind !== "phase" && (
            <Select ariaLabel="Bağlanacak aşama" value={destination} onChange={setDestination}>
              <option value="">Aşama seç</option>
              {phaseOptions.map((op) => (
                <option key={op.key} value={op.key}>
                  {op.label}
                </option>
              ))}
            </Select>
          )}
          <Button
            disabled={!newTitle.trim() || (newKind !== "phase" && !destination)}
            onClick={() => {
              const key = "user_" + crypto.randomUUID().replaceAll("-", "").slice(0, 20);
              const phase = phaseOptions.find((op) => op.key === destination);
              const root = proposal.operations.find((op) => op.type === "goal.create" || op.type === "goal.update");
              const goalRef = phase ? phase.goalRef : root?.type === "goal.update" ? root.target_id : root?.key;
              if (!goalRef) return;
              const next = [...proposal.operations];
              if (newKind === "phase")
                next.push({
                  key,
                  type: "roadmap.create",
                  goal_ref: goalRef,
                  data: {
                    title: newTitle.trim(),
                    kind: "phase",
                    position: phases.length,
                    weight: "1",
                    progress_bearing: true,
                    completion_gate: false,
                  },
                });
              else {
                const area = next.find((op) => op.type === "learning.area");
                let areaRef = area?.key;
                if (newKind === "topic" && !areaRef) {
                  areaRef = key + "_area";
                  next.push({ key: areaRef, type: "learning.area", data: { title: "Hedef çalışmaları" } });
                }
                next.push(
                  newKind === "task"
                    ? { key, type: "todo.create", data: { title: newTitle.trim(), priority: 2 } }
                    : { key, type: "learning.topic", area_ref: areaRef!, data: { title: newTitle.trim() } },
                );
                next.push({
                  key: key + "_node",
                  type: "roadmap.create",
                  goal_ref: goalRef,
                  parent_ref: destination,
                  target_ref: key,
                  data: {
                    title: newTitle.trim(),
                    kind: "record",
                    position: 0,
                    weight: "1",
                    progress_bearing: true,
                    completion_gate: false,
                  },
                });
              }
              onChange({ ...proposal, operations: next });
              setNewTitle("");
            }}
          >
            Pakete ekle
          </Button>
        </section>
      )}
    </div>
  );
}
