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
    'xtick.labelsize': 9.2,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 14.5
})

# =========================================================================
# FIGURE D14: GOLD OOD BENCHMARK - BEFORE FL vs. AFTER FL COMPARISON
# =========================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(17.5, 6.0), dpi=300)

# Models Before FL (Standalone / Centralized)
pre_models = [
    'Bi-LSTM\n(Alone)',
    'XGBoost\n(Alone)',
    'CharCNN\n(Alone)',
    'Linear SVM\n(Alone)',
    'Logistic Reg\n(Alone)',
    'Centralized\n(Pooled)',
    'Transformer\n(W_base Alone)'
]
pre_acc = [38.20, 52.15, 64.30, 68.10, 61.45, 86.24, 86.93]
pre_f1 = [32.40, 48.90, 58.70, 59.20, 51.30, 80.54, 81.74]

# Models After FL (Multi-Tenant Collaborative)
post_models = [
    'Standard\nFedAvg',
    'Hybrid\nEnsemble',
    'FedProx\n(mu=0.01)',
    'DAFL (Ours)\n(lambda=0.02)'
]
post_acc = [90.01, 90.62, 93.36, 92.76]
post_f1 = [83.36, 84.15, 87.78, 86.98]

# -------------------------------------------------------------
# Panel (a): Zero-Shot OOD Accuracy (%) - Before FL vs After FL
# -------------------------------------------------------------
x1 = np.arange(len(pre_models)) * 1.05
x2 = np.arange(len(post_models)) * 1.05 + len(pre_models) * 1.05 + 0.85

colors_pre_acc = ['#ef4444', '#ef4444', '#f87171', '#f87171', '#f87171', '#ea580c', '#94a3b8']
colors_post_acc = ['#60a5fa', '#8b5cf6', '#3b82f6', '#10b981']

bars1_pre = ax1.bar(x1, pre_acc, color=colors_pre_acc, width=0.68, edgecolor='#1e293b', linewidth=1.2, zorder=3)
bars1_post = ax1.bar(x2, post_acc, color=colors_post_acc, width=0.68, edgecolor='#1e293b', linewidth=1.2, zorder=3)

ax1.set_ylabel('Zero-Shot OOD Accuracy (%) [Higher is Better]', fontweight='bold')
ax1.set_title('(a) Zero-Shot OOD Accuracy: Pre-FL Collapse vs. Post-FL Resilience', fontweight='bold', pad=12)
all_x_ticks = list(x1) + list(x2)
all_x_labels = pre_models + post_models
ax1.set_xticks(all_x_ticks)
ax1.set_xticklabels(all_x_labels, fontweight='medium', linespacing=1.15)
ax1.set_ylim(0, 115)
ax1.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

# Section Divider Line & Labels
sep_x = (x1[-1] + x2[0]) / 2.0
ax1.axvline(sep_x, color='#94a3b8', linestyle='--', linewidth=1.5)
ax1.text((x1[0] + x1[-1])/2.0, 107, 'BEFORE FL (Standalone / Pooled)', ha='center', fontsize=9.5, fontweight='bold', color='#dc2626')
ax1.text((x2[0] + x2[-1])/2.0, 107, 'AFTER FEDERATED LEARNING', ha='center', fontsize=9.5, fontweight='bold', color='#059669')

for bar, val in zip(bars1_pre, pre_acc):
    color = '#991b1b' if val < 70 else '#0f172a'
    ax1.text(bar.get_x() + bar.get_width()/2.0, val + 1.6, f'{val:.1f}%', ha='center', va='bottom', fontsize=8.2, fontweight='bold', color=color)

for bar, val in zip(bars1_post, post_acc):
    color = '#065f46' if val > 92 else '#0f172a'
    ax1.text(bar.get_x() + bar.get_width()/2.0, val + 1.6, f'{val:.2f}%', ha='center', va='bottom', fontsize=8.5, fontweight='bold', color=color)

# -------------------------------------------------------------
# Panel (b): Zero-Shot OOD Macro F1 (%) - Gain from FL Regularization
# -------------------------------------------------------------
colors_pre_f1 = ['#fca5a5', '#fca5a5', '#fca5a5', '#fca5a5', '#fca5a5', '#fdba74', '#cbd5e1']
colors_post_f1 = ['#93c5fd', '#c084fc', '#60a5fa', '#059669']

bars2_pre = ax2.bar(x1, pre_f1, color=colors_pre_f1, width=0.68, edgecolor='#1e293b', linewidth=1.2, zorder=3)
bars2_post = ax2.bar(x2, post_f1, color=colors_post_f1, width=0.68, edgecolor='#1e293b', linewidth=1.2, zorder=3)

ax2.set_ylabel('Zero-Shot OOD Macro F1-Score (%) [Higher is Better]', fontweight='bold')
ax2.set_title('(b) Zero-Shot OOD Macro F1: Systematic Performance Gain via FL', fontweight='bold', pad=12)
ax2.set_xticks(all_x_ticks)
ax2.set_xticklabels(all_x_labels, fontweight='medium', linespacing=1.15)
ax2.set_ylim(0, 105)
ax2.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

ax2.axvline(sep_x, color='#94a3b8', linestyle='--', linewidth=1.5)
ax2.text((x1[0] + x1[-1])/2.0, 97, 'BEFORE FL (Standalone / Pooled)', ha='center', fontsize=9.5, fontweight='bold', color='#dc2626')
ax2.text((x2[0] + x2[-1])/2.0, 97, 'AFTER FEDERATED LEARNING', ha='center', fontsize=9.5, fontweight='bold', color='#059669')

for bar, val in zip(bars2_pre, pre_f1):
    ax2.text(bar.get_x() + bar.get_width()/2.0, val + 1.2, f'{val:.1f}%', ha='center', va='bottom', fontsize=8.2, fontweight='bold', color='#475569')

for bar, val in zip(bars2_post, post_f1):
    color = '#065f46' if val > 85 else '#0f172a'
    ax2.text(bar.get_x() + bar.get_width()/2.0, val + 1.2, f'{val:.2f}%', ha='center', va='bottom', fontsize=8.5, fontweight='bold', color=color)

# Annotation highlight showing gain
ax2.annotate(
    "FL Macro F1 Boost:\n+5.24% over W_base\n+6.44% over Centralized",
    xy=(x2[3], post_f1[3]),
    xytext=(x2[3] - 2.8, 62),
    fontsize=8.5,
    fontweight='bold',
    color='#065f46',
    arrowprops=dict(arrowstyle="->", color="#059669", lw=1.3),
    bbox=dict(boxstyle="round,pad=0.3", fc="#ecfdf5", ec="#10b981", lw=1.2)
)

fig.suptitle('Quantifying the Federated Generalization Leap on Purified Gold OOD (N=17,139)', fontweight='bold', fontsize=14.5, y=0.98)
plt.tight_layout()
plt.subplots_adjust(top=0.88)

fig_d14_path = os.path.join(FIG_DIR, "fig_d14_ood_pre_vs_post_fed_comparison.png")
plt.savefig(fig_d14_path, dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d14_ood_pre_vs_post_fed_comparison.png"), dpi=300, bbox_inches='tight')
plt.close()
print(f"Generated clean Figure D14: {fig_d14_path}")
