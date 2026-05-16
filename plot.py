#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

files = [
    "results-baseline.csv",
    "results-mirroring.csv",
    "results-proxying.csv",
]

dfs = []
for f in files:
    if not Path(f).exists():
        raise FileNotFoundError(f"Missing result file: {f}")
    dfs.append(pd.read_csv(f))

df = pd.concat(dfs, ignore_index=True)

summary = (
    df.groupby("scenario", as_index=False)
      .agg({
          "latency_ms": "mean",
          "cpu_mcores": "mean",
          "unrelated_kb": "mean",
          "total_kb": "mean",
      })
)

order = ["baseline", "mirroring", "proxying"]
summary["scenario"] = pd.Categorical(summary["scenario"], categories=order, ordered=True)
summary = summary.sort_values("scenario")

metrics = [
    ("latency_ms", "Average latency (ms)", "latency.png"),
    ("cpu_mcores", "Average CPU usage (mCPU)", "cpu.png"),
    ("unrelated_kb", "Average unrelated traffic (KB)", "unrelated_traffic.png"),
    ("total_kb", "Average total observed traffic (KB)", "total_traffic.png"),
]

for metric, ylabel, output in metrics:
    plt.figure()
    plt.bar(summary["scenario"].astype(str), summary[metric])
    plt.xlabel("Scenario")
    plt.ylabel(ylabel)
    plt.title(ylabel)
    plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.close()

summary.to_csv("summary.csv", index=False)

print(summary)
print("Generated: latency.png, cpu.png, unrelated_traffic.png, total_traffic.png")