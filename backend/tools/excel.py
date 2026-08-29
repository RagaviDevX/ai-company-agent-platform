from pathlib import Path

import pandas as pd


def read_excel(path: str) -> pd.DataFrame:
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path)


def analyze_csv(path: str, question: str = "") -> str:
    df = read_excel(path)
    summary = [
        f"rows={len(df)} cols={list(df.columns)}",
        df.head(20).to_string(index=False),
        "dtypes:",
        df.dtypes.astype(str).to_string(),
    ]
    if question:
        summary.insert(0, f"question={question}")
    return "\n".join(summary)
