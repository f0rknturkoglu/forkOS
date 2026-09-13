import { describe, expect, it } from "vitest";
import {
  ANNOUNCEMENT_STATUSES,
  APPLICATION_STATUSES,
  JOB_DISCOVERY_STATUSES,
  REMOTE_LABELS,
  SCORE_TONE,
  STATUSES,
  applicationStatusLabel,
  daysLeft,
  kindLabel,
  remoteKind,
  scoreBand,
} from "./labels";

/** Backend kesif dongusu (lifecycle.JOB_DISCOVERY_FLOW). */
const BACKEND_JOB_FLOW = ["discovered", "shortlisted", "dismissed", "archived", "closed"];
/** Backend duyuru dongusu (lifecycle.ANNOUNCEMENT_FLOW). */
const BACKEND_ANNOUNCEMENT_FLOW = [
  "new",
  "reviewed",
  "watching",
  "action_required",
  "applied",
  "completed",
  "expired",
  "archived",
];
/** Backend basvuru hatti (lifecycle.APPLICATION_FLOW). */
const BACKEND_APPLICATION_FLOW = [
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
  it("skor yokken 'unknown' doner: 0 ile karistirilmaz", () => {
    expect(scoreBand(null)).toBe("unknown");
    expect(scoreBand(undefined)).toBe("unknown");
    expect(scoreBand(0)).toBe("low");
  });

  it("negatif skoru elenmiş sayar", () => {
    expect(scoreBand(-1)).toBe("eliminated");
    expect(scoreBand(-100)).toBe("eliminated");
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
  it("keşif, duyuru ve başvuru kümeleri backend ile ayni", () => {
    expect(JOB_DISCOVERY_STATUSES).toEqual(BACKEND_JOB_FLOW);
    expect(ANNOUNCEMENT_STATUSES).toEqual(BACKEND_ANNOUNCEMENT_FLOW);
    expect(APPLICATION_STATUSES).toEqual(BACKEND_APPLICATION_FLOW);
    // Geriye dönük isim kesif akisini tasir; basvuru hatti AYRI kümedir.
    expect(STATUSES).toEqual(BACKEND_JOB_FLOW);
  });

  it("başvuru durumları keşif durumlarıyla karışmaz", () => {
    // İki küme yalnızca "closed" belirtecini paylaşır (her ikisinde de
    // "kapandı" anlamına gelir); dinî diğer değerler ayrıdır ve ayrı
    // kolonlarda saklanır.
    const jobOnly = ["discovered", "shortlisted", "dismissed", "archived"];
    for (const status of jobOnly) {
      expect(APPLICATION_STATUSES).not.toContain(status);
    }
    for (const status of ["interview", "offer", "accepted", "withdrawn"]) {
      expect(JOB_DISCOVERY_STATUSES).not.toContain(status);
    }
    expect(applicationStatusLabel("interview")).toBe("Görüşme");
    expect(applicationStatusLabel("discovered")).toBe("Hazırlanıyor");
  });

  it("her tür için okunabilir bir etiket var", () => {
    expect(kindLabel("job")).toBe("İş ilanı");
    expect(kindLabel("announcement")).toBe("Duyuru");
  });

  it("SCORE_TONE her band icin renk tanimli", () => {
    expect(SCORE_TONE).toEqual({
      unknown: "neutral",
      eliminated: "danger",
      low: "neutral",
      fair: "warn",
      strong: "ok",
    });
  });

  it("REMOTE_LABELS dört kanonik kovayi kapsar", () => {
    expect(Object.keys(REMOTE_LABELS).sort()).toEqual(["hybrid", "onsite", "remote", "unknown"]);
  });
});
