#!/usr/bin/env python3
"""The depth switches: what a run did, what it left out, and how to go deeper.

  python3 scripts/switches.py show [--profile lean|standard|deep|max] [--set name=value ...]
  python3 scripts/switches.py explain <switch>
  python3 scripts/switches.py disclosure RUN_DIR
  python3 scripts/switches.py docs            # writes docs/SWITCHES.md from config/

config/switches.json holds every choice that trades depth for cost, config/run_profiles.json the presets, which are only
bundles of switches. A run records its resolved switches in its manifest and in contract.json. Checks attach to switches,
never to a preset's name, because --set makes combinations. A switch never caps a verdict or a confidence level.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

DOCS = rl.ROOT / "docs" / "SWITCHES.md"
WEEK_USD = 166.0               # one weekly window of the current plan, measured on clean work
LEGACY = {"reading": "on", "digest": "off", "second_reads": "on", "effort": "xhigh", "specialists": "all",
          "verifier_sample": "full", "synthesis": "full", "audit": "full", "history_years": 10, "gap_rounds": "until_closed",
          "early_stop": "off", "canaries": "off", "spend_ceiling": None, "reading_transport": "plan"}


def registry() -> dict:
    return rl.load_json(rl.ROOT / "config" / "switches.json")


def presets() -> dict:
    return rl.load_json(rl.ROOT / "config" / "run_profiles.json")


def parse_value(text: str):
    if text.lower() in ("none", "null"):
        return None
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def problems(values: Dict[str, object]) -> List[str]:
    reg = registry()
    out = []
    for name, value in values.items():
        spec = reg["switches"].get(name)
        if spec is None:
            out.append("unknown switch %r (python3 scripts/switches.py show)" % name)
        elif isinstance(spec["values"], list) and value not in spec["values"]:
            out.append("%s cannot be %r: its values are %s" % (name, value, ", ".join(map(str, spec["values"]))))
        elif spec["values"] == "number or none" and not (value is None or isinstance(value, (int, float))):
            out.append("%s must be a number or none, not %r" % (name, value))
    for rule in reg["combinations"]:
        if all(values.get(k) == v for k, v in rule["when"].items()):
            out += ["with %s, %s must be %s (%s)" % (", ".join("%s %s" % kv for kv in rule["when"].items()), k, v, rule["why"])
                    for k, v in rule["require"].items() if values.get(k) != v]
    return out


def resolve(profile: Optional[str] = None, sets: Optional[List[str]] = None) -> dict:
    """{"profile", "values", "changed"}: a preset with any --set changes applied, checked. Reading off with a preset that
    has it on, or the reverse, moves the switches that depend on it."""
    p = presets()
    name = profile or p["default"]
    if name not in p["profiles"]:
        raise ValueError("unknown profile %r: %s" % (name, ", ".join(p["profiles"])))
    values = dict(p["profiles"][name]["switches"])
    changed = {}
    for item in sets or []:
        if "=" not in item:
            raise ValueError("--set takes name=value, not %r" % item)
        key, raw = item.split("=", 1)
        changed[key] = parse_value(raw)
    values.update(changed)
    if "reading" in changed:
        for rule in registry()["combinations"]:
            if all(values.get(k) == v for k, v in rule["when"].items()):
                values.update({k: v for k, v in rule["require"].items() if k not in changed})
        if values["reading"] == "on" and "digest" not in changed:
            values["digest"] = "off"
    bad = problems(values)
    if bad:
        raise ValueError("; ".join(bad))
    return {"profile": name, "values": values, "changed": changed}


def of_manifest(manifest: dict) -> Dict[str, object]:
    """A run's switches. A run from before switches ran with today's defaults for what it had, so old contracts stand."""
    values = dict(LEGACY, **(manifest.get("switches") or {}))
    values["reading"] = manifest.get("reading_mode", "on")
    return values


PRESET_ORDER = ("lean", "standard", "deep", "max")


def rank(name: str, value) -> Optional[int]:
    """How deep a switch value is: the first preset, lean to max, that uses it (None when no preset does)."""
    profiles = presets()["profiles"]
    for i, p in enumerate(PRESET_ORDER):
        if name in profiles.get(p, {}).get("switches", {}) and profiles[p]["switches"][name] == value:
            return i
    return None


def lighter(name: str, value, reference) -> bool:
    a, b = rank(name, value), rank(name, reference)
    return value != reference if a is None or b is None else a < b


def below(values: Dict[str, object], reference: str = "deep") -> List[dict]:
    """The switches set lighter than a preset, with what each leaves out. A switch set deeper than the preset (effort
    max, 15 years) is not lighter."""
    reg, ref = registry()["switches"], presets()["profiles"][reference]["switches"]
    return [dict(reg[k], name=k, value=values.get(k), reference=ref[k]) for k in reg
            if k in values and lighter(k, values[k], ref[k]) and k not in ("spend_ceiling", "digest", "early_stop", "reading_transport")]


def deepen_command(manifest: dict, target: str = "deep") -> str:
    return "python3 scripts/new_run.py --deepen %s --profile %s" % (manifest.get("run_id", "<RUN_ID>"), target)


def estimated_extra(manifest: dict, target: str = "deep") -> Optional[float]:
    p = presets()["profiles"]
    now, then = p.get(manifest.get("profile") or "", {}).get("estimate_usd"), p[target].get("estimate_usd")
    return None if now is None or then is None else max(then - now, 0)


def disclosure(manifest: dict) -> str:
    """The report's Depth Disclosure: what this run did not do, what that costs, and the command that goes deeper."""
    profile = manifest.get("profile") or "(set by hand)"
    values = of_manifest(manifest)
    off = below(values)
    lines = ["This run used the **%s** preset." % profile]
    if not off:
        return "\n".join(lines + ["", "Every depth switch was at its deepest setting for a reading run."]) + "\n"
    lines += ["", "| Switch | This run | Deep | What that left out | What that may cost in confidence |", "|---|---|---|---|---|"]
    lines += ["| %s | %s | %s | %s | %s |" % (o["name"], o["value"], o["reference"], o["loses"], o["confidence"]) for o in off]
    extra = estimated_extra(manifest)
    lines += ["", "**To go deeper:** `%s`%s It reuses what this run already did." % (
        deepen_command(manifest), " (about $%.0f more, an estimate, not a measurement)." % extra if extra else ".")]
    lines += ["", "No switch caps the verdict or the confidence: weigh this table in the judgment."]
    return "\n".join(lines) + "\n"


def docs_text() -> str:
    reg, pre = registry(), presets()
    names = list(pre["profiles"])
    lines = ["# Depth switches", "", "Generated by `python3 scripts/switches.py docs` from `config/switches.json` and "
             "`config/run_profiles.json`. Do not edit.", "",
             "Every choice that trades depth for cost is a switch. Pick a preset, change any switch, and the run records what "
             "it did. A switch never caps a verdict or a confidence level: every report ends with a **Depth Disclosure** "
             "listing what was off, what that may cost in confidence, and the exact command that goes deeper.", "",
             "```", 'python3 scripts/switches.py show --profile lean          # what a preset does', "python3 scripts/switches.py explain reading                # one switch",
             'python3 scripts/new_run.py ... --profile lean --set effort=xhigh', "python3 scripts/switches.py disclosure RUN_DIR            # what a run left out", "```", "",
             "## Presets", "", "| Preset | For | Estimated usage | Weeks at $%.0f | How far to trust the number |" % WEEK_USD, "|---|---|---|---|---|"]
    for n in names:
        p = pre["profiles"][n]
        usd = p.get("estimate_usd")
        lines.append("| **%s** | %s | %s | %s | %s |" % (n, p["summary"], "$%.0f" % usd if usd else "not estimated",
                                                         "%.1f" % (usd / WEEK_USD) if usd else "-", p["estimate_status"]))
    lines += ["", "The default is **%s**." % pre["default"], "", "## Switches by preset", "",
              "| Switch | %s |" % " | ".join(names), "|---|%s" % ("---|" * len(names))]
    for s in reg["switches"]:
        lines.append("| `%s` | %s |" % (s, " | ".join(str(pre["profiles"][n]["switches"].get(s)) for n in names)))
    lines += ["", "## What each switch does", ""]
    for s, spec in reg["switches"].items():
        lines += ["### `%s`" % s, "", "- **Acts in:** %s. **Values:** %s." % (
            spec["acts_in"], ", ".join(map(str, spec["values"])) if isinstance(spec["values"], list) else spec["values"]),
            "- **Buys:** %s" % spec["buys"], "- **Turning it down loses:** %s" % spec["loses"],
            "- **May cost in confidence:** %s" % spec["confidence"],
            "- **Can change:** %s." % ("at any time" if spec["frozen_after"] == "never" else "until %s" % spec["frozen_after"]), ""]
    if reg.get("not_yet_wired"):
        lines += ["## Not wired yet", "", "These do nothing yet. The release gate refuses v4.0.0 while any is listed.", ""]
        lines += ["- `%s`: %s" % kv for kv in reg["not_yet_wired"].items()] + [""]
    lines += ["## Combinations", ""] + ["- With %s, %s: %s." % (
        ", ".join("`%s` %s" % kv for kv in r["when"].items()), ", ".join("`%s` %s" % kv for kv in r["require"].items()), r["why"])
        for r in reg["combinations"]]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show")
    s.add_argument("--profile")
    s.add_argument("--set", action="append", default=[])
    e = sub.add_parser("explain")
    e.add_argument("name")
    sub.add_parser("disclosure").add_argument("run_dir")
    sub.add_parser("docs")
    a = ap.parse_args(argv)
    if a.cmd == "docs":
        DOCS.write_text(docs_text(), encoding="utf-8")
        print("wrote %s" % DOCS)
    elif a.cmd == "explain":
        spec = registry()["switches"].get(a.name)
        if not spec:
            print("unknown switch %r: %s" % (a.name, ", ".join(registry()["switches"])))
            return 1
        print(json.dumps(spec, indent=1, ensure_ascii=False))
    elif a.cmd == "disclosure":
        print(disclosure(rl.load_json(Path(a.run_dir) / rl.RUN_MANIFEST)))
    else:
        try:
            r = resolve(a.profile, a.set)
        except ValueError as exc:
            print("ERROR: %s" % exc)
            return 1
        print(json.dumps(r, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
