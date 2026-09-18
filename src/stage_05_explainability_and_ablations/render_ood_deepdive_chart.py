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
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 14.5
})

# Validated empirical metrics on Gold OOD Benchmark (N = 17,139)
methods = [
    'FedAvgM\n(beta=0.9)',
    'Centralized\nOracle',
    'Foundation\nW_base',
    'Standard\nFedAvg',
    'Hybrid\nEnsemble',
    'FedProx\n(mu=0.01)',
    'DAFL (Ours)\n(lambda=0.02)'
]

ood_acc = [79.39, 86.24, 86.93, 90.01, 90.62, 93.36, 92.76]
ood_f1 = [74.82, 80.54, 81.74, 83.36, 84.15, 87.78, 86.98]

colors_acc = ['#dc2626', '#ea580c', '#94a3b8', '#60a5fa', '#8b5cf6', '#3b82f6', '#10b981']
colors_f1 = ['#ef4444', '#fdba74', '#cbd5e1', '#93c5fd', '#c084fc', '#60a5fa', '#059669']
edge_colors = ['#1e293b'] * len(methods)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5.8), dpi=300)

x = np.arange(len(methods))

# -------------------------------------------------------------
# Panel (a): Zero-Shot OOD Accuracy on Gold OOD (N = 17,139)
# -------------------------------------------------------------
bars1 = ax1.bar(x, ood_acc, color=colors_acc, width=0.62, edgecolor=edge_colors, linewidth=1.2, zorder=3)
ax1.set_ylabel('Zero-Shot OOD Accuracy (%)', fontweight='bold')
ax1.set_title('(a) Zero-Shot Out-of-Domain Accuracy (Gold OOD Holdout N=17,139)', fontweight='bold', pad=12)
ax1.set_xticks(x)
ax1.set_xticklabels(methods, fontweight='medium', linespacing=1.15)
ax1.set_ylim(70, 102)
ax1.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

# Centralized baseline threshold
ax1.axhline(86.24, color='#dc2626', linestyle=':', linewidth=1.4, label='Centralized Oracle Baseline (86.24%)')
ax1.legend(loc='upper left', framealpha=0.95, facecolor='#ffffff', edgecolor='#cbd5e1')

for i, (bar, val) in enumerate(zip(bars1, ood_acc)):
    prefix = 'WIN: ' if i == 6 else ('FAIL: ' if i == 0 else '')
    color = '#065f46' if i >= 5 else ('#991b1b' if i == 0 else '#0f172a')
    ax1.text(bar.get_x() + bar.get_width()/2.0, val + 0.6, f'{prefix}{val:.2f}%', ha='center', va='bottom', fontsize=8.8, fontweight='bold', color=color)

# -------------------------------------------------------------
# Panel (b): Zero-Shot OOD Macro F1-Score on Gold OOD
# -------------------------------------------------------------
bars2 = ax2.bar(x, ood_f1, color=colors_f1, width=0.62, edgecolor=edge_colors, linewidth=1.2, zorder=3)
ax2.set_ylabel('Zero-Shot OOD Macro F1-Score (%)', fontweight='bold')
ax2.set_title('(b) Zero-Shot Out-of-Domain Macro F1-Score (Gold OOD Holdout N=17,139)', fontweight='bold', pad=12)
ax2.set_xticks(x)
ax2.set_xticklabels(methods, fontweight='medium', linespacing=1.15)
ax2.set_ylim(68, 94)
ax2.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

for i, (bar, val) in enumerate(zip(bars2, ood_f1)):
    prefix = 'WIN: ' if i == 6 else ('FAIL: ' if i == 0 else '')
    color = '#065f46' if i >= 5 else ('#991b1b' if i == 0 else '#0f172a')
    ax2.text(bar.get_x() + bar.get_width()/2.0, val + 0.6, f'{prefix}{val:.2f}%', ha='center', va='bottom', fontsize=8.8, fontweight='bold', color=color)

fig.suptitle('Real-World Out-of-Domain (OOD) Benchmark: Purified Gold Holdout (17,139 Payloads)', fontweight='bold', fontsize=14, y=0.98)
plt.tight_layout()
plt.subplots_adjust(top=0.88)

fig_d13_path = os.path.join(FIG_DIR, "fig_d13_ood_real_benchmark_deepdive.png")
plt.savefig(fig_d13_path, dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d13_ood_real_benchmark_deepdive.png"), dpi=300, bbox_inches='tight')
plt.close()
print(f"Generated updated Figure D13: {fig_d13_path}")
