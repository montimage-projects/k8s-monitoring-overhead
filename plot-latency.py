import csv
import glob
import matplotlib.pyplot as plt
import sys


def read(test_conf):
    csv_file = f"./results/{test_conf}-*-latency.csv"
    files = sorted(glob.glob(csv_file))

    if not files:
        print(f"No files matching {csv_file}")
        sys.exit(1)
    else:
        print(f"Found {len(files)} files {test_conf}")

    sum_response = []
    count = []
    all_values = []

    for filename in files:
        with open(filename, newline='') as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader):
                # skip first X lines which are usually effected by DNS lookup
                if i < 10:
                    continue
                i -= 10

                try:
                    value = float(row["response-time"]) * 1000  # ms
                    #dns = float(row["DNS+dialup"]) * 1000  # ms
                    #value = float(row["Response-delay"]) * 1000  # ms
                    #value -= dns
                    
                    # skip peak
                    if value > 5:
                        value = 5

                    all_values.append(value)

                    if i >= len(sum_response):
                        sum_response.append(0.0)
                        count.append(0)

                    sum_response[i] += value
                    count[i] += 1
                except Exception as e:
                    print(f"Error when reading file {filename} at\n {row}\n{e}")

    avg_response = [s / c for s, c in zip(sum_response, count)]
    x = list(range(1, len(avg_response) + 1))

    return x, avg_response, all_values, len(files)


x1, y1, raw1, z1 = read("baseline")
x2, y2, raw2, z2 = read("mirroring")
x3, y3, raw3, z3 = read("proxying")

fig, (ax_box, ax_line) = plt.subplots(
    1, 2,
    figsize=(8, 3),
    gridspec_kw={"width_ratios": [1, 2]}  # left half the width of right
)

# Define shared y-axis settings
Y_MIN = 1
Y_MAX = 6
N_TICKS = 5
Y_TICKS = [(Y_MAX-Y_MIN) * i / (N_TICKS - 1) for i in range(Y_MIN, Y_MIN + N_TICKS)]
# gives [0.0, 1.0, 2.0, 3.0, 4.0]


# --- Left: Boxplots ---
ax_box.boxplot(
    [raw1, raw2, raw3],
    labels=["Baseline", "Mirroring", "Proxying"],
    patch_artist=True,
    boxprops=dict(facecolor="lightblue", color="steelblue"),
    medianprops=dict(color="red", linewidth=2),
    whiskerprops=dict(linestyle="dashed"),
    showfliers=False,
    widths=0.6
)
# Compute medians
medians = [sorted(raw)[len(raw) // 2] for raw in [raw1, raw2, raw3]]

# Annotate each median on the boxplot
for i, median in enumerate(medians, start=1):
    ax_box.text(
        i,                        # x position (box index, 1-based)
        median,                   # y position (median value)
        f"{median:.2f}",          # label text
        ha="center",              # horizontal alignment
        va="bottom",              # vertical alignment (above the median line)
        fontsize=10,
        color="red",
        fontweight="bold"
    )
    
ax_box.set_ylabel("")           # hide y-axis label
ax_box.set_yticklabels([])      # hide y-axis tick labels
ax_box.set_ylim(Y_MIN, Y_MAX)
ax_box.set_yticks(Y_TICKS)
ax_box.yaxis.tick_right()
ax_box.yaxis.set_label_position("right")
ax_box.set_title("Response Time Distribution")
ax_box.grid(True, axis='y')

# --- Right: Line chart ---
ax_line.plot(x1, y1, linewidth=2.0,
             linestyle="solid",  label="Baseline")
ax_line.plot(x2, y2, linewidth=2.0,
             linestyle="dashed", label="Mirroring")
ax_line.plot(x3, y3, linewidth=2.0,
             linestyle="dotted", label="Proxying")
             
ax_line.set_xlabel("Request Number")
ax_line.set_ylabel("Millisecond")
ax_line.set_ylim(Y_MIN, Y_MAX)
ax_line.set_yticks(Y_TICKS)
ax_line.set_title(f"Response Time")
ax_line.legend(loc="lower right", fontsize=9, framealpha=0.8)
ax_line.grid(True)

plt.tight_layout()
plt.savefig("response-time.png", dpi=150)