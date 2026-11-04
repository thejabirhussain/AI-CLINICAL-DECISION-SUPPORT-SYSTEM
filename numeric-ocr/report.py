"""Aggregate rows_*.csv into results/summary.csv, results/summary.md and figures.

    .venv/bin/python report.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RES = Path(__file__).resolve().parent / "results"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]   # reference categorical order, fixed per engine
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
LABELS = {"tess_fast": "Tesseract 5.5 (stock, fast)", "tess_best": "Tesseract 5.5 (best)",
          "tess_fast_rescale": "stock + rescale", "tess_best_rescale": "best + rescale",
          "labnum": "fine-tuned v1", "labnum_rescale": "fine-tuned v1 + rescale",
          "labnum2": "fine-tuned", "labnum2_rescale": "fine-tuned + rescale", "rapidocr": "PP-OCR (RapidOCR)",
          "vlm-qwen2.5vl-3b": "Qwen2.5-VL 3B"}


def summarise(df: pd.DataFrame) -> dict:
    pages = df.drop_duplicates(["doc", "condition", "seed"])
    c = df[df.status == "corrupted"]
    n = len(df)
    return {"values": n, "median_CER_%": round(100 * pages.cer.median(), 2),
            "value_acc_%": round(100 * (df.status == "correct").mean(), 1),
            "wrong": len(c), "wrong_%": round(100 * len(c) / n, 2),
            "silent": int(c.silent.sum()) if len(c) else 0,
            "flag_flip": int(c.flag_flip.sum()) if len(c) else 0,
            "decimal_shift": int(c.decimal_shift.notna().sum()) if len(c) else 0,
            "missing": int((df.status == "missing").sum())}


def main() -> None:
    rows = {f.stem[5:]: pd.read_csv(f) for f in sorted(RES.glob("rows_*.csv"))}
    table = []
    for tag, df in rows.items():
        engine, testset = tag.rsplit("_", 1)
        for scope, sub in [("all", df), ("dpi<=150", df[(df.family == "resolution") & (df.dpi <= 150)])]:
            if len(sub):
                table.append({"testset": testset, "engine": engine, "scope": scope, **summarise(sub)})
    t = pd.DataFrame(table).sort_values(["testset", "scope", "engine"])
    t.to_csv(RES / "summary.csv", index=False)
    (RES / "summary.md").write_text(t.to_markdown(index=False))
    print(t.to_string(index=False))

    # Figure 1: value accuracy vs scan resolution, test A (the presented study's document)
    pick = [e for e in ["tess_fast", "tess_fast_rescale", "labnum2_rescale", "rapidocr"] if f"{e}_A" in rows]
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=150)
    for i, e in enumerate(pick):
        d = rows[f"{e}_A"]
        d = d[d.family == "resolution"]
        s = d.groupby("dpi").apply(lambda g: 100 * (g.status == "correct").mean()).sort_index()
        ax.plot(s.index, s.values, color=SERIES[i], lw=2, marker="o", ms=5, label=LABELS.get(e, e))
        ax.annotate(LABELS.get(e, e), (s.index[0], s.values[0]), xytext=(-6, 0), textcoords="offset points",
                    ha="right", va="center", fontsize=8, color=INK)
    ax.set_xlabel("scan resolution (dpi)", color=MUTED)
    ax.set_ylabel("lab values extracted exactly (%)", color=MUTED)
    ax.set_xlim(20, 310)
    ax.set_ylim(0, 102)
    ax.grid(axis="y", color=GRID, lw=0.8)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_title("Exact value accuracy vs resolution (study document, 13 analytes)", fontsize=10, color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(RES / "fig_value_accuracy_vs_dpi.png")

    # Figure 2: character accuracy hides value errors (stock engine, test A, resolution sweep)
    if "tess_fast_A" in rows:
        d = rows["tess_fast_A"]
        d = d[d.family == "resolution"]
        g = d.groupby("dpi").agg(cer=("cer", "mean"),
                                 wrong=("status", lambda s: 100 * (s != "correct").mean())).sort_index(ascending=False)
        fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=150)
        x = range(len(g))
        w = 0.38
        ax.bar([i - w / 2 - 0.01 for i in x], 100 * g.cer, w, color=SERIES[0], label="characters wrong (CER %)")
        ax.bar([i + w / 2 + 0.01 for i in x], g.wrong, w, color=SERIES[1], label="lab values wrong or missing (%)")
        ax.set_xticks(list(x), [f"{int(v)} dpi" for v in g.index], fontsize=8)
        ax.set_ylabel("%", color=MUTED)
        ax.grid(axis="y", color=GRID, lw=0.8)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
        ax.set_title("Character error rate understates numeric failure (stock Tesseract 5.5)", fontsize=10,
                     color=INK, loc="left")
        fig.tight_layout()
        fig.savefig(RES / "fig_cer_vs_value_error.png")


if __name__ == "__main__":
    main()
