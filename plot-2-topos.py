import csv
import glob
import math
import os
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

BLUE   = "#1f77b4"  # gateway probe
ORANGE = "#ff7f0e"  # node-level probe
ALL    = "all"

PROBE_COLORS = {
    "1": "#333333",  # gateway probe
    "2": "#1f77b4",  # node-level probe
    "3": "#2ca02c",  # pod-sidecar / HAProxy-side probe
    "4": "#d62728",  # node-level probe
    "5": "#9467bd",  # pod-sidecar / API-side probe
}

PROBE_LABELS = {
    "1": "Gateway",
    "2": "Node 1",
    "3": "LBalancer pod sidecar",
    "4": "Node 2",
    "5": "API pod sidecar",
}

EXTERNAL_CLIENT_IP = "192.168.1.20"

# Row-type identifiers in the MMT-Probe CSV output.
# this value is used by nmap in "haproxy-mmt-infected.yaml"
ROW_TYPE_SCAN_TRAFFIC  = 80 #port number
ROW_TYPE_SCAN_TRAFFIC  = '/hijack' #a specific path


def is_ipv6(ip):
    return ":" in ip

def is_broadcast(ip):
    return "224.0" in ip


def read_ip_pairs(folder, all_traffic=True):
    """
    Read all CSV files matching hijack-1-probe-*.csv in the given folder.

    Returns a dict: { probe_id -> { (ip_a, ip_b) -> total_packets } }
    Direction is ignored: (A,B) and (B,A) are merged into the same key.
    Self-links (src == dst) are preserved.
    """
    csv_pattern = os.path.join(folder, "hijack-1-probe-*.csv")
    files = sorted(glob.glob(csv_pattern))

    if not files:
        print(f"No files matching {csv_pattern}")
        sys.exit(1)

    row_type = "all"
    if( not all_traffic):
        row_type = "anomalous"
    print(f"Found {len(files)} files (row type {row_type})")

    probes = {}

    for filepath in files:
        with open(filepath, newline='') as f:
            reader = csv.reader(f)
            for line_num, row in enumerate(reader, start=1):
                try:
                    if row[0] != "100":
                        continue

                    # process only anomalous traffic?
                    if not all_traffic:
                        #port_src = int(row[24])
                        #port_dst = int(row[25])
                        #if port_src != ROW_TYPE_SCAN_TRAFFIC and port_dst != ROW_TYPE_SCAN_TRAFFIC :
                        #    continue
                        if len(row) < 50:
                            continue
                        http_path = row[48]
                        if http_path != ROW_TYPE_SCAN_TRAFFIC:
                            continue

                    probe_id = row[1]
                    src_ip   = row[19]
                    dst_ip   = row[20]
                    packets  = int(row[11])

                    if not src_ip or not dst_ip:
                        continue

                    # Ignore IPv6 addresses
                    if is_ipv6(src_ip) or is_ipv6(dst_ip):
                        continue

                    if is_broadcast(src_ip) or is_broadcast(dst_ip):
                        continue

                    if probe_id not in probes:
                        probes[probe_id] = {}

                    # Ignore direction by sorting the pair
                    key = tuple(sorted([src_ip, dst_ip]))
                    probes[probe_id][key] = probes[probe_id].get(key, 0) + packets

                except (IndexError, ValueError) as e:
                    print(f"Warning: skipping row {line_num}: {e}")

    return probes


def plot_topology(probe_id, flow_packets, output_dir):
    """
    Plot an undirected graph topology for a given probe's IP pairs.
    Link width reflects the number of packets. Self-links are drawn as loops.
    """
    all_ips = set()
    for src, dst in flow_packets:
        all_ips.add(src)
        all_ips.add(dst)

    ip_list = sorted(all_ips)
    n = len(ip_list)

    if n == 0:
        print(f"Probe {probe_id}: no IPs found, skipping")
        return

    # Circular layout
    positions = {}
    for i, ip in enumerate(ip_list):
        angle = 2 * math.pi * i / n
        positions[ip] = (math.cos(angle), math.sin(angle))

    # Normalise packet counts to line widths [0.5, 6.0]
    all_counts = list(flow_packets.values())
    min_pkts   = min(all_counts)
    max_pkts   = max(all_counts)
    pkt_range  = max_pkts - min_pkts if max_pkts != min_pkts else 1
    MIN_WIDTH  = 1
    MAX_WIDTH  = 6.0

    def normalise_width(pkts):
        return MIN_WIDTH + (pkts - min_pkts) / pkt_range * (MAX_WIDTH - MIN_WIDTH)

    plt.title(f"Probe {probe_id}", fontsize=10)
    fig, ax = plt.subplots(figsize=(3, 3))
    ax.set_aspect("equal")
    ax.axis("off")

    # Draw edges
    for (src, dst), pkts in flow_packets.items():
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        lw = normalise_width(pkts)

        if src == dst:
            # Self-link: small circle loop next to the node
            loop_x = x1 + 0.1
            loop_y = y1 + 0.1
            circle = plt.Circle(
                (loop_x, loop_y),
                radius=0.1,
                color="orange",
                fill=False,
                linewidth=lw
            )
            ax.add_patch(circle)
            ax.text(loop_x + 0.12, loop_y, f"{pkts:,}",
                    ha="left", va="center",
                    fontsize=8, color=ORANGE,
                    bbox=dict(facecolor="white", edgecolor="none",
                              alpha=0.7, pad=1))
        else:
            # Undirected edge: no arrowhead
            ax.annotate(
                "",
                xy=(x2, y2),
                xytext=(x1, y1),
                arrowprops=dict(
                    arrowstyle="-",
                    color=ORANGE,
                    lw=lw,
                    connectionstyle="arc3,rad=0.1"
                )
            )
            # Packet count label at midpoint
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2
            ax.text(mx, my, f"{pkts:,}",
                    ha="center", va="center",
                    fontsize=8, color=ORANGE,
                    bbox=dict(facecolor="white", edgecolor="none",
                              alpha=0.7, pad=1))

    # Draw nodes
    for ip, (x, y) in positions.items():
        ax.plot(x, y, "o",
                markersize=10,
                color=BLUE,
                markeredgecolor="black",
                markeredgewidth=0.5,
                zorder=3)
        ax.text(x, y - 0.1, ip,
                ha="center", va="top",
                fontsize=7, zorder=4)

    output_path = os.path.join(output_dir, f"topology-probe-{probe_id}.png")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Saved {output_path}")


def compute_shared_positions(probes_list, probe_ids):
    """
    Compute a single node layout (IP -> (x, y)) shared across multiple
    traffic datasets, so the same IP appears at the same position in
    every panel that uses this layout.
    """
    RADIUS = 0.5  # circle diameter halved (was 1.0)

    all_ips = set()
    for probes in probes_list:
        for probe_id in probe_ids:
            for (src, dst) in probes.get(probe_id, {}):
                all_ips.add(src)
                all_ips.add(dst)

    ip_list = sorted(all_ips)
    positions = {}

    if EXTERNAL_CLIENT_IP in ip_list:
        positions[EXTERNAL_CLIENT_IP] = (+1.6 * RADIUS, 0)
        remaining = [ip for ip in ip_list if ip != EXTERNAL_CLIENT_IP]
    else:
        remaining = ip_list

    # Circular layout for internal K8s addresses.
    n = len(remaining)
    for i, ip in enumerate(remaining):
        angle = 2 * math.pi * i / max(n, 1)
        positions[ip] = (RADIUS * math.cos(angle), RADIUS * math.sin(angle))

    return positions


def draw_global_topology_on_ax(ax, probes, probe_ids, positions, title):
    """
    Draw one global topology (all probes overlaid) onto the given matplotlib axis,
    using a precomputed, shared node layout so IP positions are consistent
    across panels.
    Each edge color indicates the probe that observed the link.
    If the same IP pair is observed by multiple probes, parallel curved
    links are drawn with different colors.

    Returns the sorted list of probe_ids actually drawn (for legend building).
    """
    ips = []
    
    edges = []
    for probe_id in probe_ids:
        for (src, dst), pkts in probes.get(probe_id, {}).items():
            edges.append((probe_id, src, dst, pkts))
            ips.append(src)
            ips.append(dst)

    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=12)

    if not edges:
        print(f"{title}: no edges found, skipping")
        # Still draw nodes so both panels show the same layout for reference.
        for ip, (x, y) in positions.items():
            node_color = "#cccccc" if ip == EXTERNAL_CLIENT_IP else BLUE
            label = f"hey\n{ip}" if ip == EXTERNAL_CLIENT_IP else ip
            ax.plot(x, y, "o", markersize=5, color=node_color,
                    markeredgecolor="black", markeredgewidth=0.7, zorder=3)
            ax.text(x, y - 0.05, label, ha="center", va="top",
                    fontsize=10, zorder=4)
        return []

    MIN_WIDTH = 2

    def normalise_width(pkts):
        return MIN_WIDTH

    # Count repeated links to assign different curvatures.
    pair_to_seen = {}
    for probe_id, src, dst, pkts in edges:
        key = tuple(sorted([src, dst]))
        idx = pair_to_seen.get(key, 0)
        pair_to_seen[key] = idx + 1

        # Alternate curvature for overlapping links.
        rad = 0.08 + 0.08 * idx
        if idx % 2 == 1:
            rad = -rad

        x1, y1 = positions[src]
        x2, y2 = positions[dst]

        color = PROBE_COLORS.get(probe_id, "gray")
        lw = normalise_width(pkts)

        if src == dst:
            print(f"skip self link {src}")
        else:
            ax.annotate(
                "",
                xy=(x2, y2),
                xytext=(x1, y1),
                arrowprops=dict(
                    arrowstyle="-",
                    color=color,
                    lw=lw,
                    alpha=1,
                    connectionstyle=f"arc3,rad={rad}"
                )
            )

    # Draw nodes (all nodes in the shared layout, even isolated ones).
    for ip, (x, y) in positions.items():
        # hide the IPs not monitoried
        if ip not in ips:
            label = ''
            node_color = '#ffffff'
        elif ip == EXTERNAL_CLIENT_IP:
            node_color = "#cccccc"
            label = f"hey\n{ip}"
        else:
            node_color = BLUE
            label = ip

        ax.plot(
            x, y, "o",
            markersize=10,
            color=node_color,
            markeredgecolor="black",
            markeredgewidth=0.7,
            zorder=3
        )
        sig = 1
        if x < 0:
            sig = -1
            
        ax.text(
            x + sig*0.05, y - 0.05, label,
            ha="center", va="top",
            fontsize=12,
            zorder=4
        )

    return sorted({probe_id for probe_id, _, _, _ in edges})


def plot_global_topology_dual(probes_scan, probes_total, output_dir):
    """
    Plot a two-panel figure: hijacked traffic topology on the left,
    total traffic topology on the right. Node positions are shared
    across both panels, and a single legend covers the probes used
    across both panels.
    """
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(11, 4.5))

    used_left  = [p for p in sorted(probes_scan.keys()) if p != ALL]
    used_right = [p for p in sorted(probes_total.keys()) if p != ALL]
    used_probe_ids = sorted(set(used_left) | set(used_right))

    # Shared layout, computed once from both datasets combined, so the
    # same IP appears at the same position in both panels.
    positions = compute_shared_positions([probes_scan, probes_total], used_probe_ids)

    drawn_left  = draw_global_topology_on_ax(ax_left,  probes_scan,  used_probe_ids, positions, "Anomalous hijacked traffic")
    drawn_right = draw_global_topology_on_ax(ax_right, probes_total, used_probe_ids, positions, "Total traffic")

    legend_probe_ids = sorted(set(drawn_left) | set(drawn_right))
    legend_items = []
    for probe_id in legend_probe_ids:
        color = PROBE_COLORS.get(probe_id, "gray")
        label = f"Probe {probe_id}: {PROBE_LABELS.get(probe_id, 'Unknown')}"
        legend_items.append(mpatches.Patch(color=color, label=label))

    fig.legend(
        handles=legend_items,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.05),
        ncol=3,
        fontsize=12,
        frameon=False
    )

    output_path = os.path.join(output_dir, "topology-anomalous-normal.png")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved {output_path}")


if __name__ == "__main__":
    folder     = sys.argv[1] if len(sys.argv) > 1 else "./results"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./"
    os.makedirs(output_dir, exist_ok=True)

    probes_total = read_ip_pairs(folder)
    probes_scan  = read_ip_pairs(folder, False)

    if not probes_total and not probes_scan:
        print("No data found.")
        sys.exit(1)

    for probe_id, flow_packets in sorted(probes_total.items()):
        total_flows   = len(flow_packets)
        total_packets = sum(flow_packets.values())
        print(f"Probe {probe_id} (total): {total_flows} flows, "
              f"{total_packets:,} total packets")
        plot_topology(probe_id, flow_packets, output_dir)

    for probe_id, flow_packets in sorted(probes_scan.items()):
        total_flows   = len(flow_packets)
        total_packets = sum(flow_packets.values())
        print(f"Probe {probe_id} (scan): {total_flows} flows, "
              f"{total_packets:,} total packets")

    print(f'probes scan: {probes_scan}')
    plot_global_topology_dual(probes_scan, probes_total, output_dir)