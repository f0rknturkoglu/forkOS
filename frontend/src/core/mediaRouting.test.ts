import { beforeEach, describe, expect, it } from "vitest";
import { entityRoute } from "./GlobalSearch";
import { notificationRoute } from "./NotificationPanel";
import { hydrateEntityRegistry } from "./entityRegistry";
import type { Entity, Notification } from "./types";
import { sourceSyncApiPath, sourceSyncQueryKey, sourceSyncRoute } from "@/modules/opportunity/SyncProgress";

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
        route: "/media/{id}",
        icon: "Film",
        searchable: true,
        linkable: true,
      },
      {
        type: "media_unit",
        label: "Bölüm",
        label_plural: "Bölümler",
        route: "/media",
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
    expect(entityRoute(entity("media_item"))).toBe("#/media/media-1");
    expect(entityRoute(entity("media_unit", "unit-1"))).toBe("#/media");
  });

  it("routes media notifications by entity or kind", () => {
    expect(
      notificationRoute(
        notification({
          entity_type: "media_item",
          entity_id: "media-1",
        }),
      ),
    ).toBe("/media/media-1");
    expect(
      notificationRoute(
        notification({
          entity_type: "media_unit",
          entity_id: "unit-1",
        }),
      ),
    ).toBe("/media");
    expect(notificationRoute(notification({ kind: "media_release" }))).toBe("/media");
    expect(notificationRoute(notification({ kind: "media_sync" }))).toBe("/media");
  });

  it("keeps opportunity sync defaults while addressing media scope explicitly", () => {
    expect(sourceSyncApiPath("opportunity")).toBe("/sources/sync");
    expect(sourceSyncRoute("opportunity")).toBe("/sources");
    expect(sourceSyncApiPath("media")).toBe("/sources/sync?scope=media");
    expect(sourceSyncRoute("media")).toBe("/sources?scope=media");
    expect(sourceSyncQueryKey("opportunity")).toEqual(["source-sync"]);
    expect(sourceSyncQueryKey("media")).toEqual(["source-sync", "media"]);
  });
});
