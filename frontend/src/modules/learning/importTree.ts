/** Enriched study trees are adapted to the existing API without losing metadata. */
const RESOURCE_TYPES: Record<string, string> = {
  documentation: "doc",
  specification: "doc",
  reference: "doc",
  official_guidance: "doc",
  video_course: "course",
  practice: "exercise",
  exam_questions: "exercise",
  official_exam: "exercise",
  assessment: "exercise",
  paper: "article",
  research_tool: "link",
};

function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label}: nesne olmalı.`);
  return value as Record<string, unknown>;
}

function knownFields(value: Record<string, unknown>, allowed: string[], label: string) {
  const unknown = Object.keys(value).filter((key) => !allowed.includes(key));
  if (unknown.length) throw new Error(`${label}: desteklenmeyen alanlar: ${unknown.join(", ")}`);
}

export function normalizeImportTree(value: unknown): Record<string, unknown> {
  const tree = object(value, "JSON");
  knownFields(tree, ["area", "topics"], "JSON");
  if (!Array.isArray(tree.topics) || !tree.topics.length)
    throw new Error('JSON içinde boş olmayan bir "topics" dizisi olmalı.');
  function resource(value: unknown): Record<string, unknown> {
    const input = object(value, "Kaynak");
    knownFields(
      input,
      [
        "title",
        "url",
        "kind",
        "note",
        "estimated_min",
        "type",
        "language",
        "description",
        "verification",
        "checked_on",
      ],
      "Kaynak",
    );
    const { type, language, description, verification, checked_on, ...seed } = input;
    const notes = [
      input.note,
      description,
      type && `Kaynak türü: ${type}`,
      language && `Dil: ${language}`,
      verification && `Doğrulama: ${verification}`,
      checked_on && `Kontrol tarihi: ${checked_on}`,
    ].filter(Boolean);
    return {
      ...seed,
      kind: input.kind ?? (typeof type === "string" ? (RESOURCE_TYPES[type] ?? type) : "link"),
      ...(notes.length ? { note: notes.join("\n") } : {}),
    };
  }
  function topic(value: unknown): Record<string, unknown> {
    const input = object(value, "Konu");
    knownFields(
      input,
      ["title", "status", "target_min", "position", "resources", "children", "practice", "completion_criteria"],
      "Konu",
    );
    const { practice, completion_criteria, resources, children, ...seed } = input;
    if (resources !== undefined && !Array.isArray(resources)) throw new Error("Kaynaklar dizi olmalı.");
    if (children !== undefined && !Array.isArray(children)) throw new Error("Alt konular dizi olmalı.");
    if (practice !== undefined && typeof practice !== "string") throw new Error("Uygulama metni yazı olmalı.");
    if (
      completion_criteria !== undefined &&
      (!Array.isArray(completion_criteria) || completion_criteria.some((item) => typeof item !== "string"))
    )
      throw new Error("Tamamlama ölçütleri yazı dizisi olmalı.");
    const normalized = (resources as unknown[] | undefined)?.map(resource) ?? [];
    const notes = [
      practice && `Uygulama\n${practice}`,
      Array.isArray(completion_criteria) &&
        completion_criteria.length &&
        `Tamamlama ölçütleri\n${completion_criteria.map((item) => `- ${item}`).join("\n")}`,
    ].filter(Boolean);
    if (notes.length)
      normalized.push({ title: "Uygulama ve tamamlama ölçütleri", kind: "exercise", note: notes.join("\n\n") });
    return {
      ...seed,
      ...(resources !== undefined || normalized.length ? { resources: normalized } : {}),
      ...(children !== undefined ? { children: (children as unknown[]).map(topic) } : {}),
    };
  }
  return { ...tree, topics: tree.topics.map(topic) };
}
