"""Portfolio quota for the `list` command.

Balance is applied at read time, never during scoring or storage. The scorer
carries no region multiplier — a posting's score is the same whichever market
it is in. The quota splits the *list*, not the score, which is what keeps a
50/50 target from silently sinking every TR posting.

Buckets:
    EU              anywhere in the EU/EEA/UK region
    TR_REMOTE       Turkey, remote
    TR_OFFICE       Turkey, office or hybrid
    OTHER_REMOTE    outside both, but remote — reachable from anywhere
    OTHER_ONSITE    outside both, on site — needs a move and a visa

The OTHER split matters more than it looks. Lumping it together buried 93
remote postings scoring 50+, including junior Python and React roles at 86,
underneath US on-site listings that are unreachable in practice. The same
distinction already applies to Turkey; it applies here for the same reason.

**The default is a floor, not a split.** Fixed shares turned out to fight the
data: a 50% TR quota kept handing half the list to postings scoring 0-20
because Turkey had nothing above 70 to give. So the list is ordered by score,
and the quota's only job is to guarantee each market a couple of slots so a
strong TR or worldwide-remote posting is never buried under a wall of EU ones.

Whatever slots a bucket does earn, it earns with postings at or above
`quota_min_score` — a bucket cannot claim room with six weak listings.

Set `quotas` in config.yaml to go back to hard shares; leaving it empty keeps
the floor behaviour.
"""

from __future__ import annotations

from collections import defaultdict

from .config import BalanceConfig
from .models import Job, JobCluster, Region, WorkMode

EU = "EU"
TR_REMOTE = "TR_REMOTE"
TR_OFFICE = "TR_OFFICE"
OTHER_REMOTE = "OTHER_REMOTE"
OTHER_ONSITE = "OTHER_ONSITE"

#: Kept so older configs and callers still resolve. Nothing produces it.
OTHER = OTHER_ONSITE

#: Display order. TR first so a strong TR posting is never buried under a wall
#: of EU ones with marginally higher scores.
BUCKET_ORDER = (TR_REMOTE, EU, OTHER_REMOTE, TR_OFFICE, OTHER_ONSITE)

BUCKET_LABELS = {
    EU: "EU",
    TR_REMOTE: "TR/remote",
    TR_OFFICE: "TR/office",
    OTHER_REMOTE: "remote/ww",
    OTHER_ONSITE: "other",
}


def bucket_for(job: Job) -> str:
    """Which quota bucket a posting belongs to."""
    if job.region is Region.TR:
        is_remote = job.remote is True or job.work_mode is WorkMode.REMOTE
        # Hybrid and unknown both count as office: the commute city still
        # matters, and most postings that are remote say so.
        return TR_REMOTE if is_remote else TR_OFFICE
    if job.region is Region.EU:
        return EU
    # Outside both target markets, remote is the difference between "apply
    # today" and "move to another continent first".
    is_remote = job.remote is True or job.work_mode is WorkMode.REMOTE
    return OTHER_REMOTE if is_remote else OTHER_ONSITE


def balance(
    pairs: list[tuple[Job, JobCluster]],
    config: BalanceConfig,
    *,
    limit: int | None = None,
) -> list[tuple[Job, JobCluster]]:
    """Re-order pairs so no bucket exceeds its share.

    Pairs must already be sorted by descending score; this only reorders and
    trims. A bucket that cannot fill its share hands the remainder to the
    others, so a thin TR week still produces a full list.
    """
    if not pairs or (not config.quotas and config.floor <= 0):
        return pairs[:limit] if limit else pairs

    buckets: dict[str, list[tuple[Job, JobCluster]]] = defaultdict(list)
    for job, cluster in pairs:
        buckets[bucket_for(job)].append((job, cluster))

    total = min(limit, len(pairs)) if limit else len(pairs)

    # A quota buys slots a bucket can fill *well*. Counting raw supply let a
    # bucket with six weak postings claim six slots: TR had no posting above
    # 70 at all, yet a 50% quota handed it half the list and pushed 80-point
    # EU roles out. Weak postings still appear — they just do not create an
    # entitlement.
    floor_score = config.quota_min_score
    quality = {
        name: sum(1 for job, _ in items if (job.score or 0) >= floor_score)
        for name, items in buckets.items()
    }
    slots = allocate_slots(quality, config, total)

    # Leftovers, if the quality-limited quota did not fill the list, go by
    # score across everything rather than being left empty.
    shortfall = total - sum(slots.values())
    if shortfall > 0:
        for name, items in buckets.items():
            spare = min(len(items) - slots.get(name, 0), shortfall)
            if spare > 0:
                slots[name] = slots.get(name, 0) + spare
                shortfall -= spare
            if shortfall <= 0:
                break

    selected = _interleave(buckets, slots, total) if config.interleave else _cap(pairs, slots)

    # The quota decides *which* postings make the list; the score decides the
    # order they are read in. Without this a 4-posting TR bucket puts an
    # 18-point sales role above a 60-point engineering one purely because the
    # round-robin reached it first.
    selected.sort(
        key=lambda pair: pair[0].score if pair[0].score is not None else -999, reverse=True
    )
    return selected


def allocate_slots(
    supply: dict[str, int],
    config: BalanceConfig,
    total: int,
) -> dict[str, int]:
    """Split `total` slots across buckets by quota, bounded by real supply.

    Runs in three passes: floor, proportional share, then redistribution of
    anything a bucket could not use.
    """
    slots: dict[str, int] = {name: 0 for name in supply}
    if total <= 0:
        return slots

    remaining = total

    # 1. floor first, so a tiny bucket is not rounded out of existence.
    #
    # Capped at half the list: with five buckets a floor of 2 would consume a
    # 10-row list entirely, leaving EU three slots while holding 82 postings
    # above 70. The floor exists to stop a market disappearing, not to hold
    # back the best results.
    if config.floor > 0:
        budget = max(1, total // 2)
        # Handed out a round at a time rather than filling each bucket in
        # turn: going bucket-by-bucket, the budget ran out on the first one or
        # two and the later buckets — the very ones the floor exists for —
        # never saw a slot.
        for pass_number in range(config.floor):
            for name in _ordered(supply):
                if budget <= 0 or remaining <= 0:
                    break
                if slots[name] > pass_number or slots[name] >= supply[name]:
                    continue
                slots[name] += 1
                remaining -= 1
                budget -= 1

    # 2. proportional share of the whole list, quota buckets only
    for name in _ordered(supply):
        share = config.quotas.get(name)
        if share is None:
            continue
        target = min(int(round(total * share)), supply[name])
        extra = max(0, target - slots[name])
        take = min(extra, remaining)
        slots[name] += take
        remaining -= take

    # 3. hand leftovers to whoever still has supply, quota buckets first
    if remaining > 0:
        quota_first = sorted(
            _ordered(supply),
            key=lambda n: (
                n not in config.quotas,
                BUCKET_ORDER.index(n) if n in BUCKET_ORDER else 99,
            ),
        )
        for name in quota_first:
            if remaining <= 0:
                break
            if name not in config.quotas and not config.allow_overflow:
                continue
            take = min(supply[name] - slots[name], remaining)
            slots[name] += take
            remaining -= take

    return slots


def _ordered(supply: dict[str, int]) -> list[str]:
    known = [b for b in BUCKET_ORDER if b in supply]
    return known + [b for b in supply if b not in BUCKET_ORDER]


def _interleave(
    buckets: dict[str, list[tuple[Job, JobCluster]]],
    slots: dict[str, int],
    total: int,
) -> list[tuple[Job, JobCluster]]:
    """Round-robin across buckets, each turn taking that bucket's best left."""
    order = _ordered(buckets)
    indices = {name: 0 for name in order}
    taken: dict[str, int] = defaultdict(int)
    result: list[tuple[Job, JobCluster]] = []

    while len(result) < total:
        progressed = False
        for name in order:
            if len(result) >= total:
                break
            if taken[name] >= slots.get(name, 0):
                continue
            index = indices[name]
            if index >= len(buckets[name]):
                continue
            result.append(buckets[name][index])
            indices[name] += 1
            taken[name] += 1
            progressed = True
        if not progressed:
            break

    return result


def _cap(
    pairs: list[tuple[Job, JobCluster]],
    slots: dict[str, int],
) -> list[tuple[Job, JobCluster]]:
    """Keep score order, dropping postings whose bucket is already full."""
    taken: dict[str, int] = defaultdict(int)
    result: list[tuple[Job, JobCluster]] = []

    for job, cluster in pairs:
        name = bucket_for(job)
        if taken[name] >= slots.get(name, 0):
            continue
        result.append((job, cluster))
        taken[name] += 1

    return result
