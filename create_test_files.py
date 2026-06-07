"""
NetProbe - Test Dosyası Oluşturucu
Senaryo 4 için farklı boyutlarda ikili test dosyaları oluşturur.

Kullanım:
    python create_test_files.py
"""

import os
import random

os.makedirs("test_files", exist_ok=True)

FILES = [
    ("test_files/small_10k.bin",  10 * 1024),
    ("test_files/medium_50k.bin", 50 * 1024),
    ("test_files/large_500k.bin", 500 * 1024),
]


def create_file(path, size_bytes):
    data = bytes(random.getrandbits(8) for _ in range(size_bytes))
    with open(path, "wb") as f:
        f.write(data)
    print(f"  Olusturuldu: {path:40s}  ({os.path.getsize(path)/1024:.0f} KB)")


if __name__ == "__main__":
    print("Test dosyalari olusturuluyor...\n")
    for path, size in FILES:
        create_file(path, size)
    print("\nHazir. Simdi: python run_experiments.py")
