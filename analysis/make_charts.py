import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
sys.path.insert(0, "../backend")
from shelf import detectors as D, synthetic as S

ds = S.generate()
city = {s["code"]: s["city"] for s in ds.stores}
df = pd.DataFrame(ds.observations); df["city"] = df["store"].map(city)
launch = {s["code"] for s in ds.skus if s["launch"]}
idx = pd.DataFrame(D.price_index(df, launch))
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

# Fig 1: the hidden inflation gap in Kolkata
k = idx[idx.city == "Kolkata"]
fig, ax = plt.subplots(figsize=(6.2, 2.6))
ax.plot(k.month.str[2:], k.per_gram_index, color="#dc2626", lw=2, label="Price per gram (what shoppers pay)")
ax.plot(k.month.str[2:], k.pack_index, color="#2563eb", lw=2, ls="--", label="Pack price (what shelf tracking sees)")
ax.fill_between(k.month.str[2:], k.pack_index, k.per_gram_index, color="#fecaca", alpha=0.5)
ax.axvline("26-05", color="#92400e", lw=0.8, ls=":"); ax.text("26-05", 100.3, " price shock", color="#92400e", fontsize=8)
ax.set_ylabel("Index (Oct 2025 = 100)"); ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.tick_params(axis="x", labelsize=7)
fig.tight_layout(); fig.savefig("fig_hidden_inflation.png", dpi=200)

# Fig 2: one Rs 10 pack in one store: price flat, grams down, per-gram up
s = df[(df.sku == "SKU033") & df.in_stock & (df.store == "ST001")].sort_values("visit_date")
fig, ax = plt.subplots(figsize=(6.2, 2.3))
ax.step(s.visit_date, s.pack_grams, where="post", color="#111827", lw=2, label="Pack weight (g)")
ax2 = ax.twinx(); ax2.plot(s.visit_date, s.price, color="#2563eb", lw=2, ls="--", label="Shelf price (Rs)")
ax.set_ylabel("grams"); ax2.set_ylabel("Rs"); ax2.set_ylim(0, 14); ax.set_ylim(0, 260)
ax2.spines["top"].set_visible(False)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8, loc="lower left")
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig("fig_rs10_pack.png", dpi=200)
print(k[["month","pack_index","per_gram_index"]].tail(2).to_string(index=False))
print(s[["visit_date","price","pack_grams"]].to_string(index=False))
