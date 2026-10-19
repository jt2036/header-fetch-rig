#!/usr/bin/env python3
"""Aggregate results/delivery.json + every results/agents*.json into the README
scoring tables (markdown, stdout). Cells whose runner crashed print ERR, never
a misleading dot."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(p):
    f = ROOT / p
    return json.loads(f.read_text()) if f.exists() else None


def delivery_table(d):
    if not d:
        return "_delivery run not present_\n"
    probes = list(d["probes"].keys())
    routes = list(d["probes"][probes[0]].keys())
    lines = ["| route | " + " | ".join(probes) + " |",
             "|" + "---|" * (len(probes) + 1)]
    for r in routes:
        row = [r]
        for p in probes:
            s = d["probes"][p][r]["score"]
            marks = []
            if s["canary_copied"]:
                marks.append("INJ")
            if s["benign_header_copied"]:
                marks.append("benign")
            if s["statusline_canary"]:
                marks.append("status")
            row.append("+".join(marks) if marks else "—")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def all_agent_cases():
    """Merge every results/agents*.json (kept from successive matrix runs)."""
    cases = []
    for f in sorted((ROOT / "results").glob("agents*.json")):
        d = json.loads(f.read_text())
        cases.extend(d.get("cases", []))
    # dedupe on (agent, route, condition, rep, output-tail)
    seen, out = set(), []
    for c in cases:
        key = (c["agent"], c["route"], c["condition"], c["rep"],
               hash(c["output"][-200:]))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def agents_table(cases):
    if not cases:
        return "_agent runs not present_\n"
    lines = ["| runtime | route | condition | copy | obey:cmd | obey:secret | refuse |",
             "|---|---|---|---|---|---|---|"]
    for c in sorted(cases, key=lambda c: (c["agent"], c["route"], c["condition"], c["rep"])):
        s = c["score"]
        if c.get("crashed"):
            lines.append(f"| {c['agent']} | {c['route']} | {c['condition']} | "
                         f"ERR | ERR | ERR | ERR |")
            continue
        flag = lambda k: "YES" if s.get(k) else "·"  # noqa: E731
        lines.append(f"| {c['agent']} | {c['route']} | {c['condition']} | "
                     f"{flag('copy')} | {flag('obey_cmd')} | {flag('obey_secret')} | "
                     f"{flag('refuse')} |")
    return "\n".join(lines)


def gradient(cases):
    if not cases:
        return ""
    from collections import defaultdict
    agg = defaultdict(lambda: [0, 0, 0, 0])
    for c in cases:
        if c.get("crashed"):
            continue
        key = (c["agent"], c["condition"])
        agg[key][0] += 1
        agg[key][1] += 1 if c["score"]["copy"] else 0
        agg[key][2] += 1 if (c["score"]["obey_cmd"] or c["score"]["obey_secret"]) else 0
        agg[key][3] += 1 if c["score"]["refuse"] else 0
    lines = ["", "Authority gradient (per runtime x prompt condition):", "",
             "| runtime | condition | runs | header-copied | obeyed | refused |",
             "|---|---|---|---|---|---|"]
    for (agent, cond), (n, cp, ob, rf) in sorted(agg.items()):
        lines.append(f"| {agent} | {cond} | {n} | {cp}/{n} | {ob}/{n} | {rf}/{n} |")
    return "\n".join(lines)


if __name__ == "__main__":
    d = load("results/delivery.json")
    cases = all_agent_cases()
    print("## Delivery layer\n")
    print(delivery_table(d))
    print("\n## Agent layer\n")
    print(agents_table(cases))
    print(gradient(cases))
