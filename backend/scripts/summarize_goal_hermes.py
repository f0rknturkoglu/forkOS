"""Summarize immutable live JSONL results; operator quality is never inferred from compile."""

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median


def summarize(rows, reviews=()):
    annotations = {(r["cohort"], r["scenario"], r["attempt"]): r for r in reviews}
    groups = defaultdict(list)
    for row in rows:
        groups[(row.get("cohort", "fixed"), row["scenario"])].append(row)
    output = []
    for (cohort, scenario), values in sorted(groups.items()):
        seconds = sorted(r["seconds"] for r in values)
        reviewed = [
            annotations[(cohort, scenario, r["attempt"])]
            for r in values
            if (cohort, scenario, r["attempt"]) in annotations
        ]
        stages = [s for r in values for s in r["diagnostics"].get("stages", [])]
        reply_parses = [s for r in values for s in r["diagnostics"].get("parse", [])]
        calls = [
            c
            for r in values
            for c in {
                c.get("run_id", str(i)): c for i, c in enumerate(r["diagnostics"]["calls"])
            }.values()
        ]
        errors = Counter(s.get("category", "unknown") for s in stages if not s["gate_valid"])
        output.append(
            {
                "cohort": cohort,
                "scenario": scenario,
                "attempts": len(values),
                "first_pass_applicable": sum(bool(r["first_attempt_applicable"]) for r in values),
                "after_at_most_one_repair_applicable": sum(bool(r["applicable"]) for r in values),
                "compiled": sum(bool(r["compiled"]) for r in values),
                "repairs": sum(bool(r["repair_attempted"]) for r in values),
                "repair_success": sum(bool(r["repair_success"]) for r in values),
                "operator_reviewed": len(reviewed),
                "operator_suitable": sum(bool(r["suitable"]) for r in reviewed),
                "calls": len(calls),
                "median_seconds": median(seconds),
                "p95_seconds": seconds[math.ceil(0.95 * len(seconds)) - 1],
                "input_bytes_total": sum(
                    c.get("input_bytes", 0) + c.get("instruction_bytes", 0) for c in calls
                ),
                "reported_input_tokens": sum(
                    (c.get("usage") or {}).get("input_tokens", 0) or 0 for c in calls
                ),
                "reported_output_tokens": sum(
                    (c.get("usage") or {}).get("output_tokens", 0) or 0 for c in calls
                ),
                "terminal_calls_without_usage": sum(
                    not c.get("usage") or not c["usage"].get("total_tokens") for c in calls
                ),
                "stage_json_passed": sum(bool(s["json_valid"]) for s in stages),
                "stage_schema_passed": sum(bool(s["schema_valid"]) for s in stages),
                "stage_gate_passed": sum(bool(s["gate_valid"]) for s in stages),
                "stages": len(stages),
                "reply_parses": len(reply_parses),
                "reply_parses_passed": sum(bool(s["valid"]) for s in reply_parses),
                "attempts_without_semantic_stages": sum(
                    not r["diagnostics"].get("stages") for r in values
                ),
                "errors": dict(errors),
                "native_noncompleted_calls": sum(c.get("status") != "completed" for c in calls),
            }
        )
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [
        json.loads(line)
        for path in args.inputs
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    reviews = json.loads(args.reviews.read_text()) if args.reviews else []
    args.output.write_text(
        json.dumps(summarize(rows, reviews), ensure_ascii=False, indent=2) + "\n"
    )
