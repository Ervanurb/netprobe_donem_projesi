"""
NetProbe - Analyzer Module
Log CSV dosyasını okur, performans metriklerini hesaplar ve grafikler üretir.

Kullanım:
    python analyzer.py --log logs/transfer_log.csv --filesize 50000 --chunksize 1024
    python analyzer.py --compare logs/scenario1.csv logs/scenario2.csv logs/scenario3.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import argparse
import os

OUTPUT_DIR = "results"


# ------------------------------------------------------------------ #
#  Metrik Hesaplama                                                    #
# ------------------------------------------------------------------ #

def compute_metrics(df: pd.DataFrame, file_size_bytes: int, chunk_size: int) -> dict:
    """
    Log DataFrame'inden performans metriklerini hesaplar.

    Returns:
        dict: throughput, goodput, completion_time, retransmission_rate, ...
    """
    success_df = df[df["event"] == "SUCCESS"]
    timeout_df = df[df["event"] == "TIMEOUT"]
    failure_df = df[df["event"] == "FAILURE"]

    total_packets     = len(success_df) + len(failure_df)
    successful_packets = len(success_df)
    failed_packets    = len(failure_df)
    timeout_count     = len(timeout_df)
    retransmit_count  = success_df["retries"].sum() + failed_packets * 5  # 5 = max retry

    # Toplam aktarım süresi (START → END arası)
    start_rows = df[df["event"] == "START"]
    end_rows   = df[df["event"] == "END"]

    if not start_rows.empty and not end_rows.empty:
        completion_time = end_rows.iloc[0]["timestamp"] - start_rows.iloc[0]["timestamp"]
    elif len(df) > 1:
        completion_time = df.iloc[-1]["timestamp"] - df.iloc[0]["timestamp"]
    else:
        completion_time = 1  # sıfıra bölme koruması

    completion_time = max(completion_time, 0.001)

    # Throughput: toplam gönderilen byte / süre
    total_sent_bytes = (successful_packets + retransmit_count) * chunk_size
    throughput = total_sent_bytes / completion_time  # byte/s

    # Goodput: başarıyla ulaşan faydalı veri / süre
    goodput = (successful_packets * chunk_size) / completion_time  # byte/s

    # Retransmission rate
    total_transmissions = successful_packets + retransmit_count
    retransmit_rate = (retransmit_count / total_transmissions * 100) if total_transmissions > 0 else 0

    # Packet loss rate
    packet_loss_rate = (failed_packets / total_packets * 100) if total_packets > 0 else 0

    # Ortalama RTT
    rtt_values = pd.to_numeric(success_df["rtt_ms"], errors="coerce").dropna()
    avg_rtt    = rtt_values.mean() if not rtt_values.empty else 0
    max_rtt    = rtt_values.max()  if not rtt_values.empty else 0

    return {
        "total_packets":      total_packets,
        "successful_packets": successful_packets,
        "failed_packets":     failed_packets,
        "timeout_count":      timeout_count,
        "retransmit_count":   int(retransmit_count),
        "retransmit_rate":    round(retransmit_rate, 2),
        "packet_loss_rate":   round(packet_loss_rate, 2),
        "completion_time_s":  round(completion_time, 3),
        "throughput_kbps":    round(throughput / 1024, 2),
        "goodput_kbps":       round(goodput / 1024, 2),
        "avg_rtt_ms":         round(avg_rtt, 2),
        "max_rtt_ms":         round(max_rtt, 2),
    }


def print_metrics(metrics: dict, label: str = ""):
    print(f"\n{'='*45}")
    if label:
        print(f"  Senaryo: {label}")
    print(f"{'='*45}")
    print(f"  Toplam paket         : {metrics['total_packets']}")
    print(f"  Başarılı paket       : {metrics['successful_packets']}")
    print(f"  Başarısız paket      : {metrics['failed_packets']}")
    print(f"  Timeout sayısı       : {metrics['timeout_count']}")
    print(f"  Yeniden gönderim     : {metrics['retransmit_count']}")
    print(f"  Retransmission rate  : %{metrics['retransmit_rate']}")
    print(f"  Packet loss rate     : %{metrics['packet_loss_rate']}")
    print(f"  Tamamlanma süresi    : {metrics['completion_time_s']}s")
    print(f"  Throughput           : {metrics['throughput_kbps']} KB/s")
    print(f"  Goodput              : {metrics['goodput_kbps']} KB/s")
    print(f"  Ortalama RTT         : {metrics['avg_rtt_ms']} ms")
    print(f"  Maks RTT             : {metrics['max_rtt_ms']} ms")


# ------------------------------------------------------------------ #
#  Grafik Üretimi — Tek Log                                           #
# ------------------------------------------------------------------ #

def plot_single(df: pd.DataFrame, metrics: dict, label: str = "transfer"):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fig = plt.figure(figsize=(14, 10))
    fig.suptitle(f"NetProbe Transfer Analizi — {label}", fontsize=14, fontweight="bold")
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35)

    success_df = df[df["event"] == "SUCCESS"].copy()
    success_df["rtt_ms"] = pd.to_numeric(success_df["rtt_ms"], errors="coerce")

    # --- 1. RTT per Packet ---
    ax1 = fig.add_subplot(gs[0, 0])
    if not success_df.empty:
        ax1.plot(success_df["seq"].values, success_df["rtt_ms"].values,
                 color="#2196F3", linewidth=1, marker="o", markersize=2)
        ax1.axhline(metrics["avg_rtt_ms"], color="red", linestyle="--",
                    linewidth=1, label=f"Ort. RTT: {metrics['avg_rtt_ms']} ms")
        ax1.legend(fontsize=8)
    ax1.set_title("RTT (Paket başına)")
    ax1.set_xlabel("Sequence Number")
    ax1.set_ylabel("RTT (ms)")
    ax1.grid(True, alpha=0.3)

    # --- 2. Olay Dağılımı (Pie) ---
    ax2 = fig.add_subplot(gs[0, 1])
    labels  = ["Başarılı", "Timeout", "Başarısız"]
    sizes   = [
        metrics["successful_packets"],
        metrics["timeout_count"],
        metrics["failed_packets"]
    ]
    colors  = ["#4CAF50", "#FF9800", "#F44336"]
    sizes   = [s for s in sizes if s > 0]
    labels2 = [l for l, s in zip(labels, [metrics["successful_packets"],
                metrics["timeout_count"], metrics["failed_packets"]]) if s > 0]
    colors2 = [c for c, s in zip(colors, [metrics["successful_packets"],
                metrics["timeout_count"], metrics["failed_packets"]]) if s > 0]
    if sizes:
        ax2.pie(sizes, labels=labels2, colors=colors2, autopct="%1.1f%%", startangle=90)
    ax2.set_title("Olay Dağılımı")

    # --- 3. Retransmission Dağılımı ---
    ax3 = fig.add_subplot(gs[1, 0])
    retry_counts = success_df["retries"].value_counts().sort_index()
    if not retry_counts.empty:
        ax3.bar(retry_counts.index.astype(str), retry_counts.values,
                color="#9C27B0", edgecolor="white")
    ax3.set_title("Retry Sayısına Göre Paket Dağılımı")
    ax3.set_xlabel("Retry Sayısı")
    ax3.set_ylabel("Paket Sayısı")
    ax3.grid(True, alpha=0.3, axis="y")

    # --- 4. Throughput vs Goodput ---
    ax4 = fig.add_subplot(gs[1, 1])
    bars = ax4.bar(["Throughput", "Goodput"],
                   [metrics["throughput_kbps"], metrics["goodput_kbps"]],
                   color=["#2196F3", "#4CAF50"], edgecolor="white", width=0.5)
    for bar, val in zip(bars, [metrics["throughput_kbps"], metrics["goodput_kbps"]]):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                 f"{val} KB/s", ha="center", va="bottom", fontsize=9)
    ax4.set_title("Throughput vs Goodput")
    ax4.set_ylabel("KB/s")
    ax4.grid(True, alpha=0.3, axis="y")

    out_path = os.path.join(OUTPUT_DIR, f"{label}_analysis.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[ANALYZER] 📊 Grafik kaydedildi: {out_path}")


# ------------------------------------------------------------------ #
#  Grafik Üretimi — Karşılaştırmalı (3 Senaryo)                      #
# ------------------------------------------------------------------ #

def plot_comparison(scenario_data: list):
    """
    scenario_data: [{"label": str, "metrics": dict}, ...]
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    labels     = [s["label"] for s in scenario_data]
    throughput = [s["metrics"]["throughput_kbps"] for s in scenario_data]
    goodput    = [s["metrics"]["goodput_kbps"]    for s in scenario_data]
    retrans    = [s["metrics"]["retransmit_rate"] for s in scenario_data]
    completion = [s["metrics"]["completion_time_s"] for s in scenario_data]
    avg_rtt    = [s["metrics"]["avg_rtt_ms"]      for s in scenario_data]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("NetProbe — Senaryo Karşılaştırması", fontsize=13, fontweight="bold")

    colors = ["#2196F3", "#4CAF50", "#FF9800"]
    x = range(len(labels))

    # Throughput vs Goodput
    ax = axes[0]
    w = 0.35
    ax.bar([i - w/2 for i in x], throughput, width=w, label="Throughput", color="#2196F3")
    ax.bar([i + w/2 for i in x], goodput,    width=w, label="Goodput",    color="#4CAF50")
    ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("KB/s"); ax.set_title("Throughput vs Goodput")
    ax.legend(); ax.grid(True, alpha=0.3, axis="y")

    # Retransmission Rate
    ax = axes[1]
    bars = ax.bar(list(x), retrans, color=colors[:len(labels)], edgecolor="white")
    for bar, val in zip(bars, retrans):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                f"%{val}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("%"); ax.set_title("Retransmission Rate")
    ax.grid(True, alpha=0.3, axis="y")

    # Tamamlanma Süresi
    ax = axes[2]
    bars = ax.bar(list(x), completion, color=colors[:len(labels)], edgecolor="white")
    for bar, val in zip(bars, completion):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{val}s", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("saniye"); ax.set_title("Tamamlanma Süresi")
    ax.grid(True, alpha=0.3, axis="y")

    out_path = os.path.join(OUTPUT_DIR, "comparison.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[ANALYZER] 📊 Karşılaştırma grafiği kaydedildi: {out_path}")


# ------------------------------------------------------------------ #
#  CLI                                                                 #
# ------------------------------------------------------------------ #

def analyze_log(log_path: str, file_size: int, chunk_size: int, label: str = None):
    df = pd.read_csv(log_path)
    label = label or os.path.splitext(os.path.basename(log_path))[0]
    metrics = compute_metrics(df, file_size, chunk_size)
    print_metrics(metrics, label)
    plot_single(df, metrics, label)
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetProbe Analyzer")
    parser.add_argument("--log",      nargs="+", required=True, help="Log CSV dosyası(ları)")
    parser.add_argument("--filesize", type=int,  default=50000, help="Dosya boyutu (byte)")
    parser.add_argument("--chunksize",type=int,  default=1024,  help="Paket boyutu (byte)")
    parser.add_argument("--labels",   nargs="+", default=None,  help="Senaryo isimleri")
    args = parser.parse_args()

    scenario_data = []
    for i, log_path in enumerate(args.log):
        label = args.labels[i] if args.labels and i < len(args.labels) else None
        metrics = analyze_log(log_path, args.filesize, args.chunksize, label)
        scenario_data.append({"label": label or f"Senaryo {i+1}", "metrics": metrics})

    if len(scenario_data) > 1:
        plot_comparison(scenario_data)