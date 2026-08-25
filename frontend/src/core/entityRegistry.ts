/**
 * Entity tipi kayit defteri (backend GET /api/registry/entity-types'in cache'i).
 *
 * Tip -> etiket/rota bilgisi YALNIZCA burada ve backend EntityTypeSpec'te
 * (AGENTS.md kural 13). Frontend'de tip->rota sabiti YAZMAZ -- GlobalSearch,
 * NotificationPanel ve RelatedPanel buradan beslenir.
 */

export interface EntityTypeSpec {
  type: string;
  label: string;
  label_plural: string;
  route: string;
  icon: string;
  searchable: boolean;
  linkable: boolean;
}

let registry: Record<string, EntityTypeSpec> = {};

export function hydrateEntityRegistry(specs: EntityTypeSpec[]): void {
  registry = Object.fromEntries(specs.map((s) => [s.type, s]));
}

/** Entity'yi kayit defterindeki rotaya cevirir; "{id}" entity id'siyle degisir. */
export function entityRoute(type: string, id: string): string {
  const spec = registry[type];
  if (!spec) return "#/";
  return spec.route.includes("{id}") ? spec.route.replace("{id}", id) : spec.route;
}

/** Tipin tekillikteki etiketi (gorunur ad). */
export function typeLabel(type: string): string {
  return registry[type]?.label ?? type;
}

export function typeSpec(type: string): EntityTypeSpec | undefined {
  return registry[type];
}
