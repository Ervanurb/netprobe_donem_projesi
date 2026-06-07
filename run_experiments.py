"""
NetProbe - Otomatik Deney Yürütücü
Tüm 12 deneyi sırayla çalıştırır ve log dosyalarını kaydeder.

Kullanım:
    python run_experiments.py
"""

import subprocess
import time
import os
import sys

PYTHON = sys.executable
PORT   = 5000

os.makedirs("logs",      exist_ok=True)
os.makedirs("results",   exist_ok=True)
os.makedirs("test_files", exist_ok=True)

# ------------------------------------------------------------
# Deney listesi
# Her satır: (isim, sunucu_args, istemci_args, dosya_yolu)
# ------------------------------------------------------------
EXPERIMENTS = [

    # Senaryo 1 — Paket boyutunun etkisi (kayıp yok)
    ("s1_chunk512",
        ["--loss", "0.0"],
        ["--chunk", "512",  "--timeout", "0.5", "--log", "logs/s1_512.csv"],
        "test.txt"),

    ("s1_chunk1024",
        ["--loss", "0.0"],
        ["--chunk", "1024", "--timeout", "0.5", "--log", "logs/s1_1024.csv"],
        "test.txt"),

    ("s1_chunk2048",
        ["--loss", "0.0"],
        ["--chunk", "2048", "--timeout", "0.5", "--log", "logs/s1_2048.csv"],
        "test.txt"),

    # Senaryo 2 — Timeout değerinin etkisi (%10 kayıp)
    ("s2_timeout02",
        ["--loss", "0.1"],
        ["--chunk", "1024", "--timeout", "0.2", "--log", "logs/s2_t02.csv"],
        "test.txt"),

    ("s2_timeout05",
        ["--loss", "0.1"],
        ["--chunk", "1024", "--timeout", "0.5", "--log", "logs/s2_t05.csv"],
        "test.txt"),

    ("s2_timeout10",
        ["--loss", "0.1"],
        ["--chunk", "1024", "--timeout", "1.0", "--log", "logs/s2_t10.csv"],
        "test.txt"),

    # Senaryo 3 — Paket kayıp oranının etkisi
    ("s3_loss0",
        ["--loss", "0.0"],
        ["--chunk", "1024", "--timeout", "0.5", "--log", "logs/s3_loss0.csv"],
        "test.txt"),

    ("s3_loss10",
        ["--loss", "0.1"],
        ["--chunk", "1024", "--timeout", "0.5", "--log", "logs/s3_loss10.csv"],
        "test.txt"),

    ("s3_loss30",
        ["--loss", "0.3"],
        ["--chunk", "1024", "--timeout", "0.5", "--log", "logs/s3_loss30.csv"],
        "test.txt"),

    # Senaryo 4 — Dosya boyutunun etkisi
    ("s4_small",
        ["--loss", "0.0"],
        ["--chunk", "1024", "--timeout", "0.5", "--log", "logs/s4_small.csv"],
        "test_files/small_10k.bin"),

    ("s4_medium",
        ["--loss", "0.0"],
        ["--chunk", "1024", "--timeout", "0.5", "--log", "logs/s4_medium.csv"],
        "test_files/medium_50k.bin"),

    ("s4_large",
        ["--loss", "0.0"],
        ["--chunk", "1024", "--timeout", "0.5", "--log", "logs/s4_large.csv"],
        "test_files/large_500k.bin"),
]


def run_experiment(name, server_extra, client_extra, filepath):
    print(f"\n{'='*52}")
    print(f"  {name}")
    print(f"{'='*52}")

    if not os.path.exists(filepath):
        print(f"  [ATLA] Dosya bulunamadi: {filepath}")
        print(f"  Once 'python create_test_files.py' calistir.")
        return False

    output_file     = f"logs/received_{name}.bin"
    server_log_path = f"logs/server_{name}.log"

    server_cmd = [
        PYTHON, "server.py",
        "--port",     str(PORT),
        "--output",   output_file,
        "--original", filepath,
    ] + server_extra

    # Sunucunun stdout/stderr'ini PIPE'a değil dosyaya yönlendiriyoruz.
    # Windows'ta PIPE buffer dolunca sunucu process kilitlenir ve port kapanır;
    # bu da istemcide WinError 10054 hatasına yol açar.
    server_log_fh = open(server_log_path, "w", encoding="utf-8")
    server_proc   = subprocess.Popen(
        server_cmd,
        stdout=server_log_fh,
        stderr=server_log_fh
    )
    time.sleep(1.0)  # Sunucunun soketi açması için bekle

    client_cmd = [
        PYTHON, "client.py",
        "--file", filepath,
        "--host", "127.0.0.1",
        "--port", str(PORT),
    ] + client_extra

    client_result = subprocess.run(client_cmd)

    # Sunucunun bitmesini bekle
    try:
        server_proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        server_proc.kill()
        print("  [UYARI] Sunucu 30s icinde bitmedi, zorla kapatildi.")

    server_log_fh.close()

    # Sunucu log özetini ekrana yaz
    if os.path.exists(server_log_path):
        with open(server_log_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if any(k in stripped for k in [
                    "Transfer tamamlandi", "butunluk", "SHA256",
                    "Istatistik", "Toplam", "Basarisiz"
                ]):
                    print(f"  [SERVER] {stripped}")

    ok = (client_result.returncode == 0)
    print(f"\n  --> {'BASARILI' if ok else 'BASARISIZ'}: {name}")
    time.sleep(1.5)  # Port TIME_WAIT'ten çıksın
    return ok


def main():
    print("=" * 52)
    print("  NetProbe - Otomatik Deney Yurututucu")
    print(f"  {len(EXPERIMENTS)} deney calistirilacak")
    print("=" * 52)

    results = []
    for name, s_args, c_args, filepath in EXPERIMENTS:
        ok = run_experiment(name, s_args, c_args, filepath)
        results.append((name, ok))

    print(f"\n{'='*52}")
    print("  OZET")
    print(f"{'='*52}")
    for name, ok in results:
        print(f"  {'OK  ' if ok else 'FAIL'} {name}")

    passed = sum(ok for _, ok in results)
    print(f"\n  {passed}/{len(results)} deney tamamlandi.")
    if passed == len(results):
        print("  Simdi: python run_analysis.py")
    else:
        print("  Bazi deneyler basarisiz. Hata icin logs/server_*.log dosyalarini kontrol et.")


if __name__ == "__main__":
    main()
