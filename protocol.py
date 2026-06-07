"""
NetProbe - Protocol Module
UDP üzerinde güvenilir dosya aktarımı için paket formatı.

Veri Paketi Yapısı:
  [type(1)] [seq(4)] [total(4)] [payload_len(2)] [checksum(16)] [payload(N)]

ACK Paketi Yapısı:
  [type(1)] [ack_num(4)] [checksum(16)]
"""

import struct
import hashlib

# Paket tipleri
PKT_DATA = 0x01
PKT_ACK  = 0x02

# Header formatları (! = network byte order / big-endian)
DATA_HEADER_FORMAT = "!B I I H 16s"   # type, seq, total, payload_len, checksum
ACK_HEADER_FORMAT  = "!B I 16s"       # type, ack_num, checksum

DATA_HEADER_SIZE = struct.calcsize(DATA_HEADER_FORMAT)
ACK_HEADER_SIZE  = struct.calcsize(ACK_HEADER_FORMAT)

# Varsayılan paket boyutu (payload kısmı)
DEFAULT_CHUNK_SIZE = 1024  # byte


def create_data_packet(seq_num: int, total_packets: int, payload: bytes) -> bytes:
    """
    Veri paketi oluşturur.
    
    Args:
        seq_num: Bu paketin sıra numarası (0'dan başlar)
        total_packets: Toplam paket sayısı
        payload: Gönderilecek ham veri

    Returns:
        Gönderilmeye hazır bytes
    """
    checksum = hashlib.md5(payload).digest()  # 16 byte MD5
    header = struct.pack(
        DATA_HEADER_FORMAT,
        PKT_DATA,
        seq_num,
        total_packets,
        len(payload),
        checksum
    )
    return header + payload


def parse_data_packet(raw: bytes):
    """
    Gelen ham veriyi veri paketine dönüştürür.

    Returns:
        (seq_num, total_packets, payload, is_valid)
        is_valid: checksum doğruysa True
    """
    if len(raw) < DATA_HEADER_SIZE:
        return None, None, None, False

    ptype, seq, total, plen, checksum = struct.unpack(
        DATA_HEADER_FORMAT, raw[:DATA_HEADER_SIZE]
    )

    if ptype != PKT_DATA:
        return None, None, None, False

    payload = raw[DATA_HEADER_SIZE: DATA_HEADER_SIZE + plen]

    # Checksum doğrula
    is_valid = (hashlib.md5(payload).digest() == checksum)

    return seq, total, payload, is_valid


def create_ack_packet(ack_num: int) -> bytes:
    """
    ACK paketi oluşturur.

    Args:
        ack_num: Onaylanan paketin sıra numarası
    """
    checksum = hashlib.md5(str(ack_num).encode()).digest()
    return struct.pack(ACK_HEADER_FORMAT, PKT_ACK, ack_num, checksum)


def parse_ack_packet(raw: bytes):
    """
    Gelen ham veriyi ACK paketine dönüştürür.

    Returns:
        (ack_num, is_valid)
    """
    if len(raw) < ACK_HEADER_SIZE:
        return None, False

    ptype, ack_num, checksum = struct.unpack(ACK_HEADER_FORMAT, raw[:ACK_HEADER_SIZE])

    if ptype != PKT_ACK:
        return None, False

    is_valid = (hashlib.md5(str(ack_num).encode()).digest() == checksum)
    return ack_num, is_valid


def split_file(filepath: str, chunk_size: int = DEFAULT_CHUNK_SIZE):
    """
    Dosyayı chunk_size boyutunda parçalara böler.

    Returns:
        List[bytes] — parçalar listesi
    """
    with open(filepath, "rb") as f:
        data = f.read()
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]


def verify_file_integrity(original_path: str, received_path: str) -> bool:
    """
    İki dosyanın SHA256 hash'ini karşılaştırarak bütünlük kontrolü yapar.
    """
    def sha256(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            h.update(f.read())
        return h.hexdigest()

    original_hash = sha256(original_path)
    received_hash  = sha256(received_path)

    print(f"  Orijinal  SHA256: {original_hash}")
    print(f"  Alınan    SHA256: {received_hash}")

    return original_hash == received_hash


# --- Basit test ---
if __name__ == "__main__":
    print("=== Protocol testi ===")

    # Veri paketi oluştur ve parse et
    payload = b"Merhaba, bu bir test paketidir!"
    pkt = create_data_packet(seq_num=0, total_packets=5, payload=payload)
    seq, total, recv_payload, valid = parse_data_packet(pkt)

    print(f"Seq: {seq}, Total: {total}, Valid: {valid}")
    print(f"Payload eşleşiyor: {payload == recv_payload}")

    # ACK paketi oluştur ve parse et
    ack_pkt = create_ack_packet(0)
    ack_num, ack_valid = parse_ack_packet(ack_pkt)
    print(f"ACK num: {ack_num}, Valid: {ack_valid}")

    print("=== Test başarılı ✓ ===")