"""Where do the detectors break? Sweep store coverage, OCR noise and visit
cadence over 3 seeds each and score against planted ground truth."""
import json
import statistics as st
import sys

import pandas as pd

sys.path.insert(0, "../backend")
from shelf import detectors as D, synthetic as S  # noqa: E402


def score(**kw):
    out = []
    for seed in (7, 11, 23):
        ds = S.generate(seed=seed, **kw)
        city = {s["code"]: s["city"] for s in ds.stores}
        df = pd.DataFrame(ds.observations)
        df["city"] = df["store"].map(city)
        pack = D.detect_pack_changes(df)
        launches = D.detect_launches(df, S.START)
        index = D.price_index(df, {l["sku"] for l in launches})
        m = D.evaluate(pack, launches, index, ds.truth)
        errs = list(m["launch_days_to_50_error"].values())
        out.append({"recall": m["shrinkflation_recall"] or 0, "precision": m["shrinkflation_precision"] or 0,
                    "false": len(m["false_pack_signals"]), "kind_ok": m["pack_events_kind_correct"] / m["pack_events_planted"],
                    "launch_err": st.mean(abs(e) for e in errs) if errs else None,
                    "shock": m["shock_found"], "shock_fa": len(m["shock_false_alarms"])})
    agg = {k: round(st.mean(o[k] for o in out if o[k] is not None), 3) for k in ("recall", "precision", "false", "kind_ok", "launch_err", "shock_fa")}
    agg["shock_found"] = f"{sum(o['shock'] for o in out)}/3"
    return agg


rows = []
for n in (10, 20, 40, 90):
    rows.append({"sweep": "stores", "value": n, **score(n_stores=n)})
for noise in (0.015, 0.05, 0.10, 0.20):
    rows.append({"sweep": "ocr_noise", "value": noise, **score(ocr_noise=noise)})
for every in (7, 14, 28):
    rows.append({"sweep": "visit_every_days", "value": every, **score(visit_every=every)})
print(pd.DataFrame(rows).to_string(index=False))
json.dump(rows, open("stress_results.json", "w"), indent=1)
