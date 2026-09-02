import { describe, expect, it } from "vitest";
import { REMOTE_LABELS, SCORE_TONE, STATUSES, daysLeft, remoteKind, scoreBand } from "./labels";

/** Backend STATUS_FLOW (app/modules/opportunity/application.py) — kart ve suzgec ayni sirayi kullanir. */
const BACKEND_STATUS_FLOW = [
  "discovered",
  "considering",
  "preparing",
  "applied",
  "interview",
  "offer",
  "accepted",
  "rejected",
  "withdrawn",
  "closed",
];

describe("scoreBand sinirlari", () => {
  it("null girdiyi null dondurur", () => {
    expect(scoreBand(null)).toBeNull();
  });

  it("negatif skoru killed sayar", () => {
    expect(scoreBand(-1)).toBe("killed");
    expect(scoreBand(-100)).toBe("killed");
  });

  it("0-39 arasini low sayar", () => {
    expect(scoreBand(0)).toBe("low");
    expect(scoreBand(39)).toBe("low");
  });

  it("40-69 arasini fair sayar", () => {
    expect(scoreBand(40)).toBe("fair");
    expect(scoreBand(69)).toBe("fair");
  });

  it("70 ve ustunu strong sayar", () => {
    expect(scoreBand(70)).toBe("strong");
    expect(scoreBand(100)).toBe("strong");
  });
});

describe("daysLeft", () => {
  const DAY = 86_400_000;

  it("gelecek tarihte pozitif gun dondurur", () => {
    expect(daysLeft(new Date(Date.now() + 3 * DAY).toISOString())).toBe(3);
  });

  it("gecmis tarihte negatif gun dondurur", () => {
    expect(daysLeft(new Date(Date.now() - 5 * DAY).toISOString())).toBe(-5);
  });

  it("null girdiyi null dondurur", () => {
    expect(daysLeft(null)).toBeNull();
  });
});

describe("remoteKind kanonik kovalari", () => {
  it("serbest remote metnini remote kovasina ceker", () => {
    expect(remoteKind("Remote - EU")).toBe("remote");
    expect(remoteKind("Uzaktan")).toBe("remote");
  });

  it("hybrid metnini hybrid kovasina ceker", () => {
    expect(remoteKind("Hybrid")).toBe("hybrid");
  });

  it("bilinen ofis sozcuklerini onsite kovasina ceker", () => {
    expect(remoteKind("Onsite")).toBe("onsite");
    expect(remoteKind("onsite")).toBe("onsite");
    expect(remoteKind("office")).toBe("onsite");
  });

  it("null girdiyi null dondurur", () => {
    expect(remoteKind(null)).toBeNull();
  });

  it("taninmayan metni null dondurur (ofis olarak varsaymaz)", () => {
    expect(remoteKind("Berlin")).toBeNull();
    expect(remoteKind("İstanbul")).toBeNull();
  });
});

describe("STATUSES ve SCORE_TONE backend ile ayni", () => {
  it("STATUSES sirasi backend STATUS_FLOW ile ayni", () => {
    expect(STATUSES).toEqual(BACKEND_STATUS_FLOW);
  });

  it("SCORE_TONE her band icin renk tanimli", () => {
    expect(SCORE_TONE).toEqual({ killed: "danger", low: "neutral", fair: "warn", strong: "ok" });
  });

  it("REMOTE_LABELS dört kanonik kovayi kapsar", () => {
    expect(Object.keys(REMOTE_LABELS).sort()).toEqual(["hybrid", "onsite", "remote", "unknown"]);
  });
});
