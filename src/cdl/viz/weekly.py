from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

import matplotlib.pyplot as plt
import pandas as pd

def load_issues(path: Path) -> pd.DataFrame:
    data = json.loads(path.read_text(encoding="utf-8"))
    df = pd.DataFrame(data)

    # Normalize missing columns + nulls
    for c in ["publisher", "series_name", "issue_number", "title", "release_date", "detail_url"]:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].fillna("")

    return df

def top_publishers(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    s = df["publisher"].replace("", "(unknown)")
    vc = s.value_counts().head(n)
    out = pd.DataFrame({"publisher": vc.index.astype(str), "count": vc.values.astype(int)})
    return out

def top_series(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    s = df["series_name"].replace("", "(unknown)")
    vc = s.value_counts().head(n)
    out = pd.DataFrame({"series_name": vc.index.astype(str), "count": vc.values.astype(int)})
    return out

def save_bar_chart(df_counts: pd.DataFrame, label_col: str, value_col: str, title: str, out_path: Path) -> None:
    labels = df_counts[label_col].tolist()
    values = df_counts[value_col].tolist()

    plt.figure(figsize=(10, 6))
    plt.barh(labels[::-1], values[::-1])
    plt.title(title)
    plt.xlabel("Count")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=200)
    plt.close()

def save_instagram_card(
    start_date: str,
    end_date: str,
    total: int,
    top_pub: Tuple[str, int] | None,
    top_series: Tuple[str, int] | None,
    out_path: Path,
) -> None:
    dpi = 150
    w_in = 1080 / dpi
    h_in = 1350 / dpi

    plt.figure(figsize=(w_in, h_in), dpi=dpi)
    plt.axis("off")

    lines = [
        "COMIC DATA LAB",
        "",
        "Weekly Releases",
        f"{start_date}  {end_date}",
        "",
        f"Total issues: {total}",
    ]
    if top_pub:
        lines.append(f"Top publisher: {top_pub[0]} ({top_pub[1]})")
    if top_series:
        lines.append(f"Top series: {top_series[0]} ({top_series[1]})")
    lines += ["", "Source: ComicVine", "Pipeline: cached + rate-limited ingest"]

    plt.text(0.5, 0.5, "\n".join(lines), ha="center", va="center", fontsize=26, wrap=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close()

def write_summary(df: pd.DataFrame, out_path: Path, start_date: str, end_date: str) -> Dict[str, Any]:
    pubs = df["publisher"].replace("", "(unknown)").value_counts()
    series = df["series_name"].replace("", "(unknown)").value_counts()

    top_pubs = top_publishers(df, n=10).to_dict(orient="records")
    top_ser = top_series(df, n=10).to_dict(orient="records")

    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total": int(len(df)),
        "unique_publishers": int(pubs.shape[0]),
        "unique_series": int(series.shape[0]),
        "top_publishers": top_pubs,
        "top_series": top_ser,
    }

    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
