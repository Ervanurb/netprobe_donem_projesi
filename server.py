"""
NetProbe - Server
UDP üzerinden dosya alır, ACK gönderir, dosyayı yeniden birleştirir.

Kullanım:
    python server.py
    python server.py --port 5001 --output alinan.bin --loss 0.1
"""

import socket
import os
import argparse
import random
import time
from protocol import (
    parse_data_packet,
    create_ack_packet,
    verify_file_integrity,
    PKT_DATA
)

DEFAULT_HOST   = "0.0.0.0"
DEFAULT_PORT   = 5000
DEFAULT_OUTPUT = "received_file"
BUFFER_SIZE    = 65535


def start_server(
    host=DEFAULT_HOST,
    port=DEFAULT_PORT,
    output_path=DEFAULT_OUTPUT,
    loss_rate=0.0,
    original_path=None
):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # SO_REUSEADDR: deneyler arasında port'un hemen serbest kalması için
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))

    print(f"[SERVER] {host}:{port} dinleniyor...")
    if loss_rate > 0:
        print(f"[SERVER] Yapay kayip orani: %{loss_rate * 100:.0f}")

    packets        = {}
    total_expected = None
    start_time     = None

    received_count  = 0
    duplicate_count = 0
    dropped_count   = 0
    ack_sent_count  = 0

    try:
        while True:
            # Windows'ta birikmiş ICMP unreachable (WinError 10054) recvfrom'dan
            # ConnectionResetError olarak fırlayabilir. Yakalayıp devam ediyoruz.
            try:
                raw, addr = sock.recvfrom(BUFFER_SIZE)
            except ConnectionResetError:
                continue

            # --- Yapay paket kaybı simülasyonu ---
            if loss_rate > 0 and random.random() < loss_rate:
                dropped_count += 1
                print(f"[SERVER] Paket yapay olarak dusuruldu (simulasyon)")
                continue

            # --- Paketi parse et ---
            seq, total, payload, valid = parse_data_packet(raw)

            if not valid or seq is None:
                print(f"[SERVER] Gecersiz/bozuk paket, yok sayiliyor")
                continue

            if start_time is None:
                start_time     = time.time()
                total_expected = total
                print(f"[SERVER] Transfer basladi. Beklenen paket sayisi: {total}")

            received_count += 1

            # --- Duplicate kontrolü ---
            if seq in packets:
                duplicate_count += 1
                print(f"[SERVER] Duplicate paket: seq={seq}, ACK tekrar gonderiliyor")
                ack = create_ack_packet(seq)
                try:
                    sock.sendto(ack, addr)
                    ack_sent_count += 1
                except ConnectionResetError:
                    pass
                continue

            # --- Yeni paket, kaydet ve ACK gönder ---
            packets[seq] = payload
            ack = create_ack_packet(seq)
            try:
                sock.sendto(ack, addr)
                ack_sent_count += 1
            except ConnectionResetError:
                # Windows: ACK gonderilemedi. Istemci retry yaparsa duplicate
                # olarak alip tekrar ACK gonderecegiz.
                pass

            progress = len(packets) / total * 100
            print(f"[SERVER] Paket alindi: seq={seq} | {len(packets)}/{total} (%{progress:.1f})")

            # --- Transfer tamamlandı mı? ---
            if len(packets) == total:
                elapsed = time.time() - start_time
                print(f"\n[SERVER] Transfer tamamlandi! Sure: {elapsed:.2f}s")
                break

    finally:
        sock.close()

    # --- Dosyayı birleştir ---
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "wb") as f:
        for i in range(total_expected):
            if i in packets:
                f.write(packets[i])
            else:
                print(f"[SERVER] Eksik paket: seq={i} — bu bolum bos birakildi")

    print(f"[SERVER] Dosya kaydedildi: {output_path}")

    # --- Bütünlük kontrolü ---
    if original_path and os.path.exists(original_path):
        print("\n[SERVER] Butunluk kontrolu yapiliyor...")
        ok = verify_file_integrity(original_path, output_path)
        if ok:
            print("[SERVER] Dosya butunlugu dogrulandi!")
        else:
            print("[SERVER] HATA: Dosya butunlugu BOZUK!")

    # --- İstatistikler ---
    print("\n[SERVER] Transfer Istatistikleri:")
    print(f"  Toplam alinan paket : {received_count}")
    print(f"  Duplicate paket     : {duplicate_count}")
    print(f"  Dusurülen paket     : {dropped_count}")
    print(f"  Gonderilen ACK      : {ack_sent_count}")
    if start_time:
        print(f"  Toplam sure         : {time.time() - start_time:.2f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetProbe UDP Server")
    parser.add_argument("--host",     default=DEFAULT_HOST,   help="Dinlenecek IP")
    parser.add_argument("--port",     type=int, default=DEFAULT_PORT, help="Port numarasi")
    parser.add_argument("--output",   default=DEFAULT_OUTPUT, help="Alinan dosyanin kaydedilecegi yol")
    parser.add_argument("--loss",     type=float, default=0.0, help="Yapay kayip orani (0.0-1.0)")
    parser.add_argument("--original", default=None, help="Butunluk kontrolu icin orijinal dosya")
    args = parser.parse_args()

    start_server(
        host=args.host,
        port=args.port,
        output_path=args.output,
        loss_rate=args.loss,
        original_path=args.original
    )
