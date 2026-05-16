import csv
import sys
import matplotlib.pyplot as plt

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} result.csv")
    sys.exit(1)

csv_file = sys.argv[1]

#response-time,DNS+dialup,DNS,Request-write,Response-delay,Response-read,status-code,offset
COLUMNS = ["response-time","DNS+dialup","DNS","Request-write","Response-delay","Response-read"]

x = []
values = {}
for col in COLUMNS:
    values[col] = []

with open(csv_file, newline='') as f:
    reader = csv.DictReader(f)

    for i, row in enumerate(reader, start=1):
        x.append(i)
        
        for col in COLUMNS:
            val = float(row[col]) * 1000
            values[col].append( val )

plt.figure(figsize=(14, 7))

for col in COLUMNS:
    plt.plot(x, values[col], label=col)

plt.xlabel("Request Number")
plt.ylabel("Time (ms)")
plt.title("hey Timing Breakdown")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig(f"{csv_file}_breakdown.png", dpi=150)
plt.show()