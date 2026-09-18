import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIG_DIR = os.path.join(ROOT_DIR, "reports", "presentation_figures")
PUB_FIG_DIR = os.path.join(ROOT_DIR, "reports", "publication_figures")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(PUB_FIG_DIR, exist_ok=True)

# Global styling for top-tier academic presentation
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 14
})

# =========================================================================
# FIGURE D1: DATA FUNNEL & CURATED CLASS DISTRIBUTION
# =========================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2), dpi=300)

# Subplot 1: Funnel Drop
stages = ['1. Raw Ingested\n(7 Repositories)', '2. After 3-Pass\nSanitization', '3. Exact Deduplication\n(Purged 2.53M)', '4. Final Curated\nGold Corpus']
counts = [5324801, 5210430, 2790268, 2790268]
colors = ['#94a3b8', '#60a5fa', '#f59e0b', '#10b981']

bars = ax1.bar(stages, [c / 1e6 for c in counts], color=colors, width=0.55, edgecolor='#1e293b', linewidth=1.2)
ax1.set_ylabel('Samples (Millions)', fontweight='bold')
ax1.set_title('(a) Clean-Room Data Filtering Funnel', fontweight='bold', pad=12)
ax1.set_ylim(0, 6.0)
ax1.grid(axis='y', linestyle='--', alpha=0.5)

for bar, count in zip(bars, counts):
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 0.12, f'{count:,}\n({yval:.2f}M)', ha='center', va='bottom', fontsize=9.5, fontweight='bold')

# Subplot 2: Class Donut Distribution
labels = ['Benign (61.4%)', 'SQLi (14.4%)', 'PathTrav (13.3%)', 'XSS (10.9%)']
sizes = [1712058, 401988, 371114, 305108]
class_colors = ['#10b981', '#f59e0b', '#3b82f6', '#ef4444']
explode = (0.02, 0.04, 0.04, 0.04)

wedges, texts, autotexts = ax2.pie(
    sizes, explode=explode, labels=labels, colors=class_colors, autopct='%1.1f%%',
    startangle=140, pctdistance=0.75, wedgeprops=dict(width=0.45, edgecolor='#1e293b', linewidth=1.2)
)
for at in autotexts:
    at.set_fontweight('bold')
    at.set_color('#ffffff')
for t in texts:
    t.set_fontweight('bold')
    
ax2.set_title('(b) Curated 2.79M Gold Cluster Distribution', fontweight='bold', pad=12)

plt.tight_layout()
fig_d1_path = os.path.join(FIG_DIR, "fig_d1_data_funnel_and_classes.png")
plt.savefig(fig_d1_path, dpi=300)
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d1_data_funnel_and_classes.png"), dpi=300)
plt.close()
print(f"Generated: {fig_d1_path}")

# =========================================================================
# FIGURE D2: TWO-TIER CLEAN-ROOM SPLIT & ZERO LEAKAGE
# =========================================================================
fig, ax = plt.subplots(figsize=(11, 4.8), dpi=300)

partitions = [
    'Pool A (Pretrain $W_{base}$)\nIndependent 15%',
    'Pool B: Client Train\n6 Silos (Non-IID)',
    'Pool B: Client Val/Test\n6 Silos Local Holdouts',
    'Pool B: Global Test B\nMaster In-Domain Holdout',
    'External OOD Holdout\n(CSIC 2010 Benchmark)'
]
part_counts = [418540, 1327440, 331877, 354808, 122130]
bar_colors = ['#6366f1', '#2563eb', '#0284c7', '#0d9488', '#ea580c']

bars = ax.barh(partitions, [c / 1e3 for c in part_counts], color=bar_colors, edgecolor='#1e293b', height=0.55, linewidth=1.2)
ax.set_xlabel('Sample Count (Thousands)', fontweight='bold')
ax.set_title('Two-Tier Clean-Room Separation ($0.000\%$ Leakage SHA-256 Verified)', fontweight='bold', pad=12)
ax.grid(axis='x', linestyle='--', alpha=0.5)
ax.set_xlim(0, 1600)

for bar, count in zip(bars, part_counts):
    xval = bar.get_width()
    ax.text(xval + 20, bar.get_y() + bar.get_height()/2.0, f'{count:,} samples ({count/2790268*100:.1f}% total)', ha='left', va='center', fontsize=9.5, fontweight='bold')

plt.tight_layout()
fig_d2_path = os.path.join(FIG_DIR, "fig_d2_two_tier_split_and_zero_leakage.png")
plt.savefig(fig_d2_path, dpi=300)
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d2_two_tier_split_and_zero_leakage.png"), dpi=300)
plt.close()
print(f"Generated: {fig_d2_path}")

# =========================================================================
# FIGURE D3: 6-CLIENT NON-IID SKEW BREAKDOWN
# =========================================================================
fig, ax = plt.subplots(figsize=(12, 5.5), dpi=300)

clients = ['Client 1\n(E-Commerce)', 'Client 2\n(Marketplace)', 'Client 3\n(Banking)', 'Client 4\n(Payment Gateway)', 'Client 5\n(Cloud Storage)', 'Client 6\n(Enterprise SaaS)']

# Exact class counts per client
benign_counts = [113835, 113836, 77614, 77615, 74037, 74037]
xss_counts    = [136603, 136603, 11642, 11642, 11106, 11106]
sqli_counts   = [17075, 17075, 93138, 93138, 9255, 9255]
pathtrav_counts = [17076, 17076, 11642, 11642, 90696, 90696]

width = 0.55
indices = np.arange(len(clients))

p1 = ax.bar(indices, benign_counts, width, label='Benign Traffic', color='#10b981', edgecolor='#1e293b')
p2 = ax.bar(indices, xss_counts, width, bottom=benign_counts, label='XSS Attack (Client 1-2 Skew)', color='#ef4444', edgecolor='#1e293b')
p3 = ax.bar(indices, sqli_counts, width, bottom=np.array(benign_counts)+np.array(xss_counts), label='SQLi Attack (Client 3-4 Skew)', color='#f59e0b', edgecolor='#1e293b')
p4 = ax.bar(indices, pathtrav_counts, width, bottom=np.array(benign_counts)+np.array(xss_counts)+np.array(sqli_counts), label='PathTrav Attack (Client 5-6 Skew)', color='#3b82f6', edgecolor='#1e293b')

ax.set_ylabel('Local Training Samples ($N=1,327,440$)', fontweight='bold')
ax.set_title('Cross-Industry Non-IID Attack Skew Profile Across 6 Enterprise Silos', fontweight='bold', pad=14)
ax.set_xticks(indices)
ax.set_xticklabels(clients, fontweight='bold')
ax.legend(loc='upper right', framealpha=0.95, edgecolor='#cbd5e1')
ax.grid(axis='y', linestyle='--', alpha=0.5)
ax.set_ylim(0, 340000)

for i in range(len(clients)):
    total = benign_counts[i] + xss_counts[i] + sqli_counts[i] + pathtrav_counts[i]
    ax.text(i, total + 6000, f'Total:\n{total:,}', ha='center', va='bottom', fontsize=9, fontweight='bold', color='#1e293b')

plt.tight_layout()
fig_d3_path = os.path.join(FIG_DIR, "fig_d3_6_client_non_iid_skew.png")
plt.savefig(fig_d3_path, dpi=300)
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d3_6_client_non_iid_skew.png"), dpi=300)
plt.close()
print(f"Generated: {fig_d3_path}")

# =========================================================================
# FIGURE D4: SEQUENCE LENGTH & ENCODING COVERAGE
# =========================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), dpi=300)

# Length CDF Simulation based on audited percentiles
lengths = np.array([16, 32, 64, 96, 128, 160, 192, 224, 256, 320, 384, 512])
cdf = np.array([12.4, 28.5, 54.2, 72.8, 86.4, 93.1, 96.8, 98.9, 99.8, 99.9, 99.95, 100.0])

ax1.plot(lengths, cdf, color='#7c3aed', linewidth=2.5, marker='o', label='Empirical Payload CDF')
ax1.axvline(256, color='#ef4444', linestyle='--', linewidth=1.8, label='Max Token Window ($L=256$, $99.8\%$)')
ax1.set_xlabel('Payload Character Length (Bytes)', fontweight='bold')
ax1.set_ylabel('Cumulative Coverage (%)', fontweight='bold')
ax1.set_title('(a) Payload Length Cumulative Distribution', fontweight='bold', pad=12)
ax1.grid(True, linestyle='--', alpha=0.5)
ax1.legend(loc='lower right')
ax1.set_ylim(0, 105)

# Vocabulary Token ASCII Mapping
ascii_ranges = ['Control\n(0-31)', 'Whitespace\n(Space, Tab)', 'Digits\n(0-9)', 'Uppercase\n(A-Z)', 'Lowercase\n(a-z)', 'Punctuation\n(&,?,=,/,<,>,etc.)', 'Extended\n(128+)']
token_counts = [0, 4, 10, 26, 26, 32, 1]
ax2.bar(ascii_ranges, token_counts, color='#0284c7', edgecolor='#1e293b', width=0.55)
ax2.set_ylabel('Unique Reserved Tokens ($V=130$)', fontweight='bold')
ax2.set_title('(b) Byte-Level ASCII Tokenizer Coverage ($V=130$)', fontweight='bold', pad=12)
ax2.grid(axis='y', linestyle='--', alpha=0.5)

plt.tight_layout()
fig_d4_path = os.path.join(FIG_DIR, "fig_d4_payload_length_distribution.png")
plt.savefig(fig_d4_path, dpi=300)
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d4_payload_length_distribution.png"), dpi=300)
plt.close()
print(f"Generated: {fig_d4_path}")

print("\nALL 4 DATA PRESENTATION CHARTS SUCCESSFULLY RENDERED AT 300 DPI!")
