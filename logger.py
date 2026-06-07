"""
NetProbe - Logger Module
Transfer sırasında oluşan olayları CSV formatında kaydeder.

Kullanım (client.py içinden):
    from logger import TransferLogger
    logger = TransferLogger("logs/transfer_log.csv")
    logger.log_success(seq=0, retries=0, rtt_ms=12.3)
    logger.log_timeout(seq=1, retry_no=1)
    logger.log_failure(seq=2)
    logger.close()
"""

import csv
import time
import os


class TransferLogger:
    """
    Transfer olaylarını CSV dosyasına kaydeden logger sınıfı.

    Kaydedilen olaylar:
        SUCCESS  — ACK başarıyla alındı
        TIMEOUT  — ACK alınamadı, timeout oluştu
        FAILURE  — Maksimum retry aşıldı, paket gönderilemedi
        DUPLICATE— Duplicate paket alındı (server tarafı)
        DROPPED  — Paket yapay olarak düşürüldü (simülasyon)
        START    — Transfer başladı
        END      — Transfer tamamlandı
    """

    FIELDNAMES = ["timestamp", "elapsed_ms", "event", "seq", "retries", "rtt_ms", "note"]

    def __init__(self, filepath: str = "logs/transfer_log.csv"):
        self.filepath = filepath
        self.start_time = time.time()

        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)

        self._file = open(filepath, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self.FIELDNAMES)
        self._writer.writeheader()

        # Sayaçlar
        self.count_success   = 0
        self.count_timeout   = 0
        self.count_failure   = 0
        self.count_duplicate = 0
        self.count_dropped   = 0

        self._log("START", seq=-1, retries=0, rtt_ms="", note="Transfer başladı")
        print(f"[LOGGER] Log dosyası açıldı: {filepath}")

    # ------------------------------------------------------------------ #
    #  Public metodlar                                                     #
    # ------------------------------------------------------------------ #

    def log_success(self, seq: int, retries: int, rtt_ms: float):
        """ACK başarıyla alındı."""
        self.count_success += 1
        self._log("SUCCESS", seq=seq, retries=retries, rtt_ms=round(rtt_ms, 3))

    def log_timeout(self, seq: int, retry_no: int):
        """Timeout oluştu."""
        self.count_timeout += 1
        self._log("TIMEOUT", seq=seq, retries=retry_no, rtt_ms="", note=f"timeout #{retry_no}")

    def log_failure(self, seq: int):
        """Maksimum retry aşıldı, paket gönderilemedi."""
        self.count_failure += 1
        self._log("FAILURE", seq=seq, retries=-1, rtt_ms="", note="max retry aşıldı")

    def log_duplicate(self, seq: int):
        """Duplicate paket alındı (server tarafı)."""
        self.count_duplicate += 1
        self._log("DUPLICATE", seq=seq, retries=0, rtt_ms="", note="duplicate, yok sayıldı")

    def log_dropped(self, seq: int):
        """Paket yapay olarak düşürüldü (simülasyon)."""
        self.count_dropped += 1
        self._log("DROPPED", seq=seq, retries=0, rtt_ms="", note="simülasyon kaybı")

    def log_transfer_end(self, total_packets: int, elapsed_sec: float,
                          throughput_kbps: float, goodput_kbps: float):
        """Transfer sona erdi, özet satırı ekle."""
        note = (
            f"total={total_packets} elapsed={elapsed_sec:.2f}s "
            f"throughput={throughput_kbps:.2f}KB/s goodput={goodput_kbps:.2f}KB/s"
        )
        self._log("END", seq=-1, retries=0, rtt_ms="", note=note)

    def summary(self) -> dict:
        """Sayaçların özetini döndürür."""
        return {
            "success":   self.count_success,
            "timeout":   self.count_timeout,
            "failure":   self.count_failure,
            "duplicate": self.count_duplicate,
            "dropped":   self.count_dropped,
        }

    def close(self):
        """Log dosyasını kapat."""
        self._file.flush()
        self._file.close()
        print(f"[LOGGER] Log kapatıldı → {self.filepath}")
        self._print_summary()

    # ------------------------------------------------------------------ #
    #  Private metodlar                                                    #
    # ------------------------------------------------------------------ #

    def _log(self, event: str, seq: int, retries: int, rtt_ms, note: str = ""):
        now = time.time()
        elapsed_ms = round((now - self.start_time) * 1000, 1)
        self._writer.writerow({
            "timestamp":  round(now, 4),
            "elapsed_ms": elapsed_ms,
            "event":      event,
            "seq":        seq,
            "retries":    retries,
            "rtt_ms":     rtt_ms,
            "note":       note,
        })
        self._file.flush()  # anlık yazım — çökme durumunda veri kaybolmasın

    def _print_summary(self):
        print("\n[LOGGER] 📋 Olay Özeti:")
        print(f"  SUCCESS   : {self.count_success}")
        print(f"  TIMEOUT   : {self.count_timeout}")
        print(f"  FAILURE   : {self.count_failure}")
        print(f"  DUPLICATE : {self.count_duplicate}")
        print(f"  DROPPED   : {self.count_dropped}")


# ------------------------------------------------------------------ #
#  Test                                                                #
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    import os
    logger = TransferLogger("logs/test_log.csv")

    logger.log_success(seq=0,  retries=0, rtt_ms=11.2)
    logger.log_success(seq=1,  retries=1, rtt_ms=23.5)
    logger.log_timeout(seq=2,  retry_no=1)
    logger.log_timeout(seq=2,  retry_no=2)
    logger.log_success(seq=2,  retries=2, rtt_ms=45.1)
    logger.log_failure(seq=3)
    logger.log_duplicate(seq=1)
    logger.log_dropped(seq=4)
    logger.log_transfer_end(total_packets=5, elapsed_sec=1.2,
                             throughput_kbps=42.0, goodput_kbps=38.5)
    logger.close()

    print("\nLog dosyası içeriği:")
    with open("logs/test_log.csv") as f:
        print(f.read())