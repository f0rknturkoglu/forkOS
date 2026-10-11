import { beforeEach, describe, expect, it } from "vitest";
import { entityRoute } from "./GlobalSearch";
import { notificationRoute } from "./NotificationPanel";
import { hydrateEntityRegistry } from "./entityRegistry";
import type { Entity, Notification } from "./types";
import { sourceSyncApiPath, sourceSyncQueryKey, sourceSyncRoute } from "@/core/SyncProgress";

function entity(type: string, id = "media-1"): Entity {
  return {
    id,
    type,
    title: "Medya",
    created_at: "2026-08-23T09:00:00Z",
    updated_at: "2026-08-23T10:00:00Z",
  };
}

function notification(overrides: Partial<Notification>): Notification {
  return {
    id: 1,
    kind: "other",
    title: "Bildirim",
    body: null,
    entity_id: null,
    entity_type: null,
    importance: 1,
    created_at: "2026-08-23T10:00:00Z",
    read_at: null,
    ...overrides,
  };
}

describe("media integration routing", () => {
  beforeEach(() => {
    hydrateEntityRegistry([
      {
        type: "media_item",
        label: "Medya",
        label_plural: "Medyalar",
        route: "/activity",
        icon: "Film",
        searchable: true,
        linkable: true,
      },
      {
        type: "media_unit",
        label: "Bölüm",
        label_plural: "Bölümler",
        route: "/activity",
        icon: "FileVideo",
        searchable: true,
        linkable: true,
      },
      {
        type: "opportunity",
        label: "Fırsat",
        label_plural: "Fırsatlar",
        route: "/opportunities?focus={id}",
        icon: "Target",
        searchable: true,
        linkable: true,
      },
    ]);
  });

  it("routes searchable media entities from the entity-type registry", () => {
    expect(entityRoute(entity("media_item"))).toBe("#/activity");
    expect(entityRoute(entity("media_unit", "unit-1"))).toBe("#/activity");
  });

  it("routes media notifications by entity or kind", () => {
    expect(
      notificationRoute(
        notification({
          entity_type: "media_item",
          entity_id: "media-1",
        }),
      ),
    ).toBe("/activity");
    expect(
      notificationRoute(
        notification({
          entity_type: "media_unit",
          entity_id: "unit-1",
        }),
      ),
    ).toBe("/activity");
    expect(notificationRoute(notification({ kind: "media_release" }))).toBe("/activity");
    expect(notificationRoute(notification({ kind: "media_sync" }))).toBe("/activity");
  });

  it("keeps opportunity sync defaults while addressing media scope explicitly", () => {
    expect(sourceSyncApiPath("opportunity")).toBe("/sources/sync");
    expect(sourceSyncRoute("opportunity")).toBe("/sources");
    expect(sourceSyncQueryKey("opportunity")).toEqual(["source-sync"]);
  });
});
