"""raw ERP exports -> clean lines + quarantine -> SQL metrics -> output/"""
from pathlib import Path

from spend.analyze import analyze, save
from spend.normalize import normalize

OUT = Path("output")

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    clean, quarantine = normalize(Path("data/raw"), Path("data/reference"))
    clean.to_csv(OUT / "lines_clean.csv", index=False)
    quarantine.to_csv(OUT / "quarantine.csv", index=False)
    metrics = analyze(clean, quarantine)
    save(metrics, OUT / "metrics.json")
    print(f"{len(clean)} clean lines, {len(quarantine)} quarantined, metrics written to output/metrics.json")
