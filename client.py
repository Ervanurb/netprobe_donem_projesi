"""
NetProbe - Client
Dosyayı parçalara böler, UDP ile gönderir.
ACK bekler, timeout olursa yeniden gönderir (max 5 deneme).

Kullanım:
    python client.py --file gonder.txt
    python client.py --file gonder.txt --host 127.0.0.1 --port 5000 --chunk 512 --timeout 0.5
"""

import socket
import time
import os
import argparse
import csv
from protocol import (
    create_data_packet,
    parse_ack_packet,
    split_file,
    DEFAULT_CHUNK_SIZE
)

DEFAULT_HOST      = "127.0.0.1"
DEFAULT_PORT      = 5000
DEFAULT_TIMEOUT   = 0.5
DEFAULT_MAX_RETRY = 5
BUFFER_SIZE       = 65535
DEFAULT_LOG_FILE  = "logs/transfer_log.csv"


def send_file(
    filepath,
    host=DEFAULT_HOST,
    port=DEFAULT_PORT,
    chunk_size=DEFAULT_CHUNK_SIZE,
    timeout=DEFAULT_TIMEOUT,
    max_retry=DEFAULT_MAX_RETRY,
    log_file=DEFAULT_LOG_FILE
):
    if not os.path.exists(filepath):
        print(f"[CLIENT] HATA: Dosya bulunamadi: {filepath}")
        return

    os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else ".", exist_ok=True)

    chunks    = split_file(filepath, chunk_size)
    total     = len(chunks)
    file_size = os.path.getsize(filepath)

    print(f"[CLIENT] Dosya      : {filepath} ({file_size} byte)")
    print(f"[CLIENT] Paket      : {total} adet x {chunk_size} byte")
    print(f"[CLIENT] Hedef      : {host}:{port} | Timeout: {timeout}s | Max retry: {max_retry}")
    print(f"[CLIENT] Transfer basliyor...\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    log_rows         = []
    total_sent       = 0
    total_ack        = 0
    total_timeout    = 0
    total_retransmit = 0
    failed_packets   = []

    start_time = time.time()

    for seq, chunk in enumerate(chunks):
        packet  = create_data_packet(seq, total, chunk)
        success = False
        retries = 0

        while retries <= max_retry:
            send_time = time.time()
            sock.sendto(packet, (host, port))
            total_sent += 1

            if retries > 0:
                total_retransmit += 1
                print(f"[CLIENT] Yeniden gonderim: seq={seq}, deneme={retries}/{max_retry}")

            try:
                ack_raw, _ = sock.recvfrom(BUFFER_SIZE)
                rtt = time.time() - send_time

                ack_num, ack_valid = parse_ack_packet(ack_raw)

                if ack_valid and ack_num == seq:
                    total_ack += 1
                    success    = True
                    print(f"[CLIENT] ACK alindi: seq={seq} | RTT: {rtt*1000:.1f}ms | Retry: {retries}")
                    log_rows.append({
                        "timestamp": send_time,
                        "event":     "SUCCESS",
                        "seq":       seq,
                        "retries":   retries,
                        "rtt_ms":    round(rtt * 1000, 3),
                        "note":      ""
                    })
                    break
                else:
                    retries += 1

            except (socket.timeout, ConnectionResetError):
                # socket.timeout      : normal zaman asimi
                # ConnectionResetError: Windows'a ozgu UDP davranisi (WinError 10054)
                #   Sunucu portu gecici olarak kapandiginda Windows ICMP unreachable
                #   gonderiyor; bunu timeout gibi ele alip yeniden gonderiyoruz.
                total_timeout += 1
                retries       += 1
                print(f"[CLIENT] Timeout: seq={seq}, deneme={retries}/{max_retry}")
                log_rows.append({
                    "timestamp": send_time,
                    "event":     "TIMEOUT",
                    "seq":       seq,
                    "retries":   retries,
                    "rtt_ms":    "",
                    "note":      f"timeout deneme {retries}"
                })

        if not success:
            failed_packets.append(seq)
            print(f"[CLIENT] BASARISIZ: seq={seq} — max retry asildi!")
            log_rows.append({
                "timestamp": time.time(),
                "event":     "FAILURE",
                "seq":       seq,
                "retries":   max_retry,
                "rtt_ms":    "",
                "note":      "max retry asildi"
            })

    elapsed = time.time() - start_time
    sock.close()

    with open(log_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["timestamp", "event", "seq", "retries", "rtt_ms", "note"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(log_rows)

    print(f"\n[CLIENT] Log kaydedildi: {log_file}")

    successful = total - len(failed_packets)
    throughput = (total_sent * chunk_size) / elapsed if elapsed > 0 else 0
    goodput    = (successful * chunk_size)  / elapsed if elapsed > 0 else 0
    ret_rate   = (total_retransmit / total_sent * 100) if total_sent > 0 else 0

    print("\n[CLIENT] Transfer Istatistikleri:")
    print(f"  Toplam paket         : {total}")
    print(f"  Basarili             : {successful}")
    print(f"  Basarisiz            : {len(failed_packets)}")
    print(f"  Toplam gonderim      : {total_sent}")
    print(f"  Yeniden gonderim     : {total_retransmit}")
    print(f"  Timeout sayisi       : {total_timeout}")
    print(f"  Retransmission rate  : %{ret_rate:.1f}")
    print(f"  Toplam sure          : {elapsed:.2f}s")
    print(f"  Throughput           : {throughput/1024:.2f} KB/s")
    print(f"  Goodput              : {goodput/1024:.2f} KB/s")

    if failed_packets:
        print(f"\n[CLIENT] Basarisiz paketler: {failed_packets}")
    else:
        print(f"\n[CLIENT] Tum paketler basariyla gonderildi!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetProbe UDP Client")
    parser.add_argument("--file",    required=True,                          help="Gonderilecek dosya")
    parser.add_argument("--host",    default=DEFAULT_HOST,                   help="Server IP")
    parser.add_argument("--port",    type=int,   default=DEFAULT_PORT,       help="Server port")
    parser.add_argument("--chunk",   type=int,   default=DEFAULT_CHUNK_SIZE, help="Paket boyutu (byte)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,    help="ACK timeout (saniye)")
    parser.add_argument("--retry",   type=int,   default=DEFAULT_MAX_RETRY,  help="Max yeniden gonderim")
    parser.add_argument("--log",     default=DEFAULT_LOG_FILE,               help="Log dosyasi yolu")
    args = parser.parse_args()

    send_file(
        filepath=args.file,
        host=args.host,
        port=args.port,
        chunk_size=args.chunk,
        timeout=args.timeout,
        max_retry=args.retry,
        log_file=args.log
    )
