"""
NetProbe - Otomatik Analiz ve Grafik Üretici
Tüm senaryo log dosyalarını okur, grafikleri üretir.

Kullanım:
    python run_analysis.py
"""

import subprocess
import sys
import os

PYTHON = sys.executable

SCENARIOS = [
    {
        "logs":      ["logs/s1_512.csv", "logs/s1_1024.csv", "logs/s1_2048.csv"],
        "labels":    ["512B", "1024B", "2048B"],
        "filesize":  50000,
        "chunksize": 1024,
        "desc":      "Senaryo 1 - Paket Boyutu Etkisi",
    },
    {
        "logs":      ["logs/s2_t02.csv", "logs/s2_t05.csv", "logs/s2_t10.csv"],
        "labels":    ["0.2s", "0.5s", "1.0s"],
        "filesize":  50000,
        "chunksize": 1024,
        "desc":      "Senaryo 2 - Timeout Etkisi",
    },
    {
        "logs":      ["logs/s3_loss0.csv", "logs/s3_loss10.csv", "logs/s3_loss30.csv"],
        "labels":    ["%0 kayip", "%10 kayip", "%30 kayip"],
        "filesize":  50000,
        "chunksize": 1024,
        "desc":      "Senaryo 3 - Kayip Orani Etkisi",
    },
    {
        "logs":      ["logs/s4_small.csv", "logs/s4_medium.csv", "logs/s4_large.csv"],
        "labels":    ["10KB", "50KB", "500KB"],
        "filesize":  50000,
        "chunksize": 1024,
        "desc":      "Senaryo 4 - Dosya Boyutu Etkisi",
    },
]


def run_scenario(s):
    print(f"\n  {s['desc']}")

    missing = [f for f in s["logs"] if not os.path.exists(f)]
    if missing:
        print(f"  [ATLA] Eksik log dosyasi: {missing}")
        return False

    cmd = [
        PYTHON, "analyzer.py",
        "--log",       *s["logs"],
        "--labels",    *s["labels"],
        "--filesize",  str(s["filesize"]),
        "--chunksize", str(s["chunksize"]),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  Grafik uretildi -> results/ klasorunde")
    else:
        print(f"  Hata: {result.stderr[:300]}")
    return result.returncode == 0


if __name__ == "__main__":
    print("=" * 52)
    print("  NetProbe - Otomatik Analiz")
    print("=" * 52)

    os.makedirs("results", exist_ok=True)
    ok_count = sum(run_scenario(s) for s in SCENARIOS)

    print(f"\n  {ok_count}/{len(SCENARIOS)} senaryo analiz edildi.")
    print(f"  Grafikler -> results/ klasorunde")
