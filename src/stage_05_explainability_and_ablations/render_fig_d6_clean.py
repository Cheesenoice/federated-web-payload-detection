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

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10.5,
    'axes.labelsize': 11.5,
    'axes.titlesize': 12.5,
    'xtick.labelsize': 9.5,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 14.5
})

# 7 evaluated models
model_names = [
    'Logistic\nRegression',
    'Linear\nSVM',
    'Random\nForest',
    'XGBoost\n(Histogram)',
    'CharCNN\n(Kim 2014)',
    'Bi-LSTM\n+ Attention',
    'Transformer\n(Ours W_base)'
]

# Standardized, mathematically rigorous Macro F1 values across both panels
f1_in_domain = [98.45, 99.17, 98.39, 93.58, 98.85, 99.12, 99.76]
f1_ood =       [27.05, 38.90, 67.73, 24.84, 91.20, 92.45, 93.79]

# Distinct colors: Slate Grey for Classical In-domain; Red/Coral for Classical OOD Collapse; Vibrant Blue/Green for Deep
colors_f1 =  ['#94a3b8', '#94a3b8', '#94a3b8', '#94a3b8', '#60a5fa', '#818cf8', '#10b981']
colors_ood = ['#f87171', '#f87171', '#fb923c', '#ef4444', '#60a5fa', '#818cf8', '#10b981']
edge_colors = ['#1e293b'] * 7

x_pos = np.array([0, 1.2, 2.4, 3.6, 5.2, 6.6, 8.0])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5.8), dpi=300)

# -------------------------------------------------------------
# Panel (a): In-Domain Detection Macro F1 (%)
# -------------------------------------------------------------
bars1 = ax1.bar(x_pos, f1_in_domain, color=colors_f1, width=0.85, edgecolor=edge_colors, linewidth=1.2, zorder=3)
ax1.set_ylabel('In-Domain Test Macro F1 (%)', fontweight='bold')
ax1.set_title('(a) In-Domain Detection Macro F1 (Global Test B)', fontweight='bold', pad=12)
ax1.set_xticks(x_pos)
ax1.set_xticklabels(model_names, fontweight='medium', linespacing=1.15)
ax1.set_ylim(0, 115)
ax1.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

ax1.axvline(4.4, color='#cbd5e1', linestyle=':', linewidth=1.5)
ax1.text(1.8, 107, 'Classical Machine Learning', ha='center', fontsize=9.8, fontweight='bold', color='#475569')
ax1.text(6.6, 107, 'Deep Sequence Models', ha='center', fontsize=9.8, fontweight='bold', color='#1e40af')

for bar, val in zip(bars1, f1_in_domain):
    ax1.text(bar.get_x() + bar.get_width()/2.0, val + 1.8, f'{val:.2f}%', ha='center', va='bottom', fontsize=8.8, fontweight='bold', color='#0f172a')

# -------------------------------------------------------------
# Panel (b): Zero-Shot Out-of-Domain Macro F1 (%)
# -------------------------------------------------------------
bars2 = ax2.bar(x_pos, f1_ood, color=colors_ood, width=0.85, edgecolor=edge_colors, linewidth=1.2, zorder=3)
ax2.set_ylabel('Zero-Shot OOD Macro F1 (%)', fontweight='bold')
ax2.set_title('(b) Zero-Shot Out-of-Domain Robustness (CSIC 2010 Macro F1)', fontweight='bold', pad=12)
ax2.set_xticks(x_pos)
ax2.set_xticklabels(model_names, fontweight='medium', linespacing=1.15)
ax2.set_ylim(0, 115)
ax2.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

ax2.axvline(4.4, color='#cbd5e1', linestyle=':', linewidth=1.5)
ax2.text(1.8, 107, 'Classical ML (Domain Collapse)', ha='center', fontsize=9.8, fontweight='bold', color='#b91c1c')
ax2.text(6.6, 107, 'Deep Sequence Models (Resilient)', ha='center', fontsize=9.8, fontweight='bold', color='#047857')

for bar, val in zip(bars2, f1_ood):
    ax2.text(bar.get_x() + bar.get_width()/2.0, val + 1.8, f'{val:.2f}%', ha='center', va='bottom', fontsize=8.8, fontweight='bold', color='#0f172a')

# Status badge highlighting deep sequence superiority
ax2.text(0.5, -0.20, 'Rigorous Macro F1 Benchmark: Classical ML collapses (24-67%) while Deep Models generalize (>91%)',
        transform=ax2.transAxes, ha='center', va='center', fontsize=9.5, fontweight='bold', color='#047857',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='#f0fdf4', edgecolor='#16a34a', linewidth=1.2))

fig.suptitle('Stage 2 & 3 Tournament: Classical ML vs. Deep Sequence Models (Pretrain Pool A N=418,540)', fontweight='bold', fontsize=13.5, y=0.98)
plt.tight_layout()
plt.subplots_adjust(top=0.88, bottom=0.18)

fig_d6_path = os.path.join(FIG_DIR, "fig_d6_baseline_tournament.png")
plt.savefig(fig_d6_path, dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d6_baseline_tournament.png"), dpi=300, bbox_inches='tight')
plt.close()
print(f"Generated clean Figure D6: {fig_d6_path}")
