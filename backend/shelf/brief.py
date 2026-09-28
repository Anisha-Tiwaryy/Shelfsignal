"""Weekly 'what changed on shelves' brief.

With GEMINI_API_KEY set, the detector output (numbers only, no raw images or
store identities) is sent to Gemini to write the brief. Without a key, a
deterministic template writes it, so the endpoint always works and tests
never depend on the network. The response says which path produced it.
"""
from __future__ import annotations

import json
import urllib.request

from django.conf import settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"


def facts_from(pack, launches, index) -> dict:
    shrink = [p for p in pack if p["kind"] == "shrinkflation"]
    latest = {}
    for r in index:
        if r["city"] not in latest or r["month"] > latest[r["city"]]["month"]:
            latest[r["city"]] = r
    gaps = {c: round(r["per_gram_index"] - r["pack_index"], 2) for c, r in latest.items()}
    return {
        "shrinkflation": [{k: p[k] for k in ("sku", "grams_before", "grams_after", "per_gram_change_pct", "confidence")}
                          for p in shrink],
        "fastest_launch": launches[0]["sku"] if launches else None,
        "launch_days_to_50": {l["sku"]: l["days_to_50"] for l in launches},
        "hidden_inflation_gap_pts": gaps,
        "shocks": [(r["city"], r["month"]) for r in index if r["shock"]],
    }


def template_brief(f: dict) -> str:
    lines = [f"{len(f['shrinkflation'])} products shrank their pack while keeping the shelf price flat."]
    if f["shrinkflation"]:
        top = max(f["shrinkflation"], key=lambda x: x["per_gram_change_pct"])
        lines.append(f"Largest: {top['sku']} went {top['grams_before']}g to {top['grams_after']}g, "
                     f"a {top['per_gram_change_pct']}% rise in price per gram, seen in "
                     f"{round(top['confidence'] * 100)}% of stores carrying it.")
    if f["hidden_inflation_gap_pts"]:
        city, gap = max(f["hidden_inflation_gap_pts"].items(), key=lambda kv: kv[1])
        lines.append(f"Hidden inflation: per-gram prices run {gap} index points above pack prices in {city}.")
    if f["fastest_launch"]:
        lines.append(f"Fastest launch: {f['fastest_launch']} reached half of stores in "
                     f"{f['launch_days_to_50'][f['fastest_launch']]} days.")
    for city, month in f["shocks"]:
        lines.append(f"Price shock: {city} jumped sharply in {month}.")
    return " ".join(lines)


def gemini_brief(f: dict, key: str) -> str:
    prompt = ("You are a retail analyst. Write a 5-sentence brief for a consumer-goods strategy team using ONLY "
              "these numbers. Do not invent figures.\n" + json.dumps(f, default=str))
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    req = urllib.request.Request(GEMINI_URL.format(key=key), data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def build_brief(pack, launches, index) -> dict:
    f = facts_from(pack, launches, index)
    if settings.GEMINI_API_KEY:
        try:
            return {"source": "gemini-1.5-flash", "text": gemini_brief(f, settings.GEMINI_API_KEY), "facts": f}
        except Exception as exc:  # network or quota failure falls back, and says so
            return {"source": f"template (Gemini failed: {type(exc).__name__})", "text": template_brief(f), "facts": f}
    return {"source": "template (no GEMINI_API_KEY set)", "text": template_brief(f), "facts": f}
