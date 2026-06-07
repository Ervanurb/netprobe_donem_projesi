# NetProbe

UDP Tabanlı Güvenilir Dosya Aktarımı, Trafik İzleme ve Ağ Performans Analiz Platformu

Bursa Teknik Üniversitesi — Bilgisayar Mühendisliği Bölümü  
Bilgisayar Ağları Dersi Dönem Projesi

GitHub: https://github.com/Ervanurb/netprobe_donem_projesi

---

## Kurulum

```bash
pip install pandas matplotlib
```

Python 3.8+ gereklidir.

---

## Klasör Yapısı

```
netprobe/
├── protocol.py           # Paket formatı, checksum, dosya bölme/birleştirme
├── client.py             # UDP istemci — dosya gönderir
├── server.py             # UDP sunucu — dosya alır, ACK gönderir
├── logger.py             # Transfer olay kaydedici (TransferLogger sınıfı)
├── analyzer.py           # Metrik hesaplama ve grafik üretimi
│
├── create_test_files.py  # Senaryo 4 için test dosyaları oluşturur
├── run_experiments.py    # Tüm 12 deneyi otomatik çalıştırır
├── run_analysis.py       # Tüm grafikleri otomatik üretir
│
├── test.txt              # 50 KB test dosyası
├── test_files/           # Farklı boyutlarda test dosyaları (create_test_files çıktısı)
├── logs/                 # Transfer log CSV dosyaları + sunucu logları
└── results/              # Üretilen analiz grafikleri (PNG)
```

---

## Kullanım

### Adım 1 — Test dosyalarını oluştur

```bash
python create_test_files.py
```

### Adım 2 — Tüm deneyleri çalıştır

```bash
python run_experiments.py
```

12 deney sırayla çalışır (~3-5 dakika). Her deney:
- Sunucuyu başlatır
- İstemciyi çalıştırır
- Log dosyasını `logs/` klasörüne kaydeder
- Sunucuyu kapatır

### Adım 3 — Grafikleri üret

```bash
python run_analysis.py
```

Grafikler `results/` klasörüne kaydedilir.

---

## Manuel Kullanım (tek dosya)

İki ayrı terminal aç:

```bash
# Terminal 1 — Sunucu
python server.py --output alinan.bin

# Terminal 2 — İstemci
python client.py --file test.txt
```

---

## Parametreler

### server.py

| Parametre    | Varsayılan    | Açıklama                              |
|-------------|---------------|---------------------------------------|
| `--port`    | 5000          | Dinlenecek port                       |
| `--output`  | received_file | Alınan dosyanın kaydedileceği yol     |
| `--loss`    | 0.0           | Yapay kayıp oranı (0.0 – 1.0)        |
| `--original`| —             | Bütünlük kontrolü için orijinal dosya |

### client.py

| Parametre    | Varsayılan            | Açıklama                          |
|-------------|-----------------------|-----------------------------------|
| `--file`    | —                     | Gönderilecek dosya (zorunlu)      |
| `--host`    | 127.0.0.1             | Sunucu IP adresi                  |
| `--port`    | 5000                  | Sunucu port numarası              |
| `--chunk`   | 1024                  | Paket payload boyutu (byte)       |
| `--timeout` | 0.5                   | ACK bekleme süresi (saniye)       |
| `--retry`   | 5                     | Maksimum yeniden gönderim sayısı  |
| `--log`     | logs/transfer_log.csv | Log dosyası yolu                  |

---

## Deney Senaryoları

| Senaryo   | Değişen Parametre      | Sabit Değerler                   |
|-----------|------------------------|----------------------------------|
| Senaryo 1 | Paket boyutu           | loss=0, timeout=0.5s             |
| Senaryo 2 | Timeout süresi         | chunk=1024, loss=%10             |
| Senaryo 3 | Kayıp oranı            | chunk=1024, timeout=0.5s         |
| Senaryo 4 | Dosya boyutu           | chunk=1024, timeout=0.5s, loss=0 |

## Proje Ekibi

Erva Nur Bostancı

Tuğba Çevik

Eren Bezek
