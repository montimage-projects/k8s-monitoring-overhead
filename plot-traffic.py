import csv
import glob
import matplotlib.pyplot as plt
import numpy as np
import sys

def count_pkt_volume(filepath):
    pkt   = 0
    bytes = 0
    with open(filepath, newline='') as csvfile:
        reader = csv.reader(csvfile)
        #next(reader)  # skip header row
        for line_num, row in enumerate(reader, start=2):
            try:
                if row[0] == "100" and len(row) > 30:
                    pkt   += int(row[11])
                    bytes += int(row[9])
                elif row[0] == "99" and len(row) > 10:
                    pkt   += int(row[10])
                    bytes += int(row[8])
            except (IndexError, ValueError) as e:
                print(f"Warning: skipping row {line_num} ({row}): {e}")
    return pkt, bytes


def read_one_probe(test_conf, probe_id):
    csv_file = f"./results/{test_conf}-*-probe-{probe_id}.csv"
    files = sorted(glob.glob(csv_file))

    if not files:
        print(f"No files matching {csv_file}")
        sys.exit(1)
    else:
        print(f" - {probe_id}: Found {len(files)} files {test_conf}")

    total_pkt = 0.0
    total_vol = 0.0

    for filename in files:
        pkt, vol = count_pkt_volume(filename)
        total_pkt += pkt
        total_vol += vol

    count = len(files)
    return total_pkt / count, total_vol / count


def read(test_conf):
    print(f"Reading {test_conf}:")
    sum_pkt = []
    sum_vol = []
    for i in range(1, 6):
        pkt, vol = read_one_probe(test_conf, i)
        sum_pkt.append(pkt)
        sum_vol.append(vol)
    return sum_pkt, sum_vol


def plot_bar_chart(x, y1, y2, ylabel, title, filename,
                   label1="Mirroring", label2="Proxying"):
    width = 0.35
    offsets = np.arange(len(x))

    fig, ax = plt.subplots(figsize=(4, 3))
    bars1 = ax.bar(offsets - width / 2, y1, width, label=label1)
    bars2 = ax.bar(offsets + width / 2, y2, width, label=label2)


    # Add space between highest bar and top frame border
    top = max(max(y1), max(y2)) * 1.3
    space = top / 40
    ax.set_ylim(top=top)

    # Annotate values on top of each bar
    for bar in bars1:
        ax.text(
            bar.get_x() + bar.get_width() / 2,  # x: center of bar
            bar.get_height() + space,                    # y: top of bar
            f"{bar.get_height():.0f}",           # label: rounded integer
            ha="center", va="bottom",
            fontsize=10, rotation=90
        )

    for bar in bars2:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + space,
            f"{bar.get_height():.0f}",
            ha="center", va="bottom",
            fontsize=10, rotation=90
        )



    ax.set_xlabel("Probe Position")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(offsets)
    ax.set_xticklabels([f"{i}" for i in x])
    ax.legend(loc="upper left")
    ax.grid(True, axis='y')

    fig.tight_layout()
    fig.savefig(filename, dpi=150)
    print(f"Saved {filename}")


pkt1, vol1 = read("mirroring")
pkt2, vol2 = read("proxying")

vol1 = [ c / 1000 for c in vol1]
vol2 = [ c / 1000 for c in vol2]

x = range(1, 6)

plot_bar_chart(x, pkt1, pkt2,
               ylabel="Packets",
               title="Packets per Probe Position",
               filename="traffic-packets.png")

plot_bar_chart(x, vol1, vol2,
               ylabel="Volume (KB)",
               title="Volume per Probe Position",
               filename="traffic-volume.png")
