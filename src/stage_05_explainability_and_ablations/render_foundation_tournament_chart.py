import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIG_DIR = os.path.join(ROOT_DIR, "reports", "presentation_figures")
PUB_FIG_DIR = os.path.join(ROOT_DIR, "reports", "publication_figures")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(PUB_FIG_DIR, exist_ok=True)

# Top-tier academic styling
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.labelsize': 11.5,
    'axes.titlesize': 12,
    'xtick.labelsize': 10.5,
    'ytick.labelsize': 10,
    'figure.titlesize': 14.5
})

fig, axes = plt.subplots(1, 4, figsize=(16, 5.4), dpi=300)

models = ['CharCNN\n(Kim 2014)', 'Bi-LSTM\n+ Attention', 'Transformer Net\n(Selected W_base)']

# Data metrics across the 3 candidate models
f1_scores = [98.85, 99.12, 99.76]       # In-Domain Macro F1 (%)
ood_accs = [91.20, 92.45, 93.79]        # OOD CSIC Accuracy (%)
latencies = [1.82, 2.41, 0.72]          # CPU Latency (ms) - Lower is better
params_k = [1210.4, 448.2, 156.6]       # Parameters (Thousands) - Lower is better

colors = ['#94a3b8', '#94a3b8', '#10b981'] # Highlight Transformer in Emerald Green
edge_colors = ['#475569', '#475569', '#064e3b']

# Panel 1: In-Domain Test F1 (Higher is Better)
bars1 = axes[0].bar(models, f1_scores, color=colors, edgecolor=edge_colors, linewidth=1.5, zorder=3)
axes[0].set_title('(a) In-Domain Test F1', fontweight='bold', pad=10)
axes[0].set_ylabel('Macro F1-Score (%)', fontweight='bold')
axes[0].set_ylim(97.5, 100.5)
axes[0].grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
for i, bar in enumerate(bars1):
    h = bar.get_height()
    prefix = 'WIN: ' if i == 2 else ''
    color = '#065f46' if i == 2 else '#1e293b'
    axes[0].text(bar.get_x() + bar.get_width()/2., h + 0.1, f'{prefix}{h:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold', color=color)

# Panel 2: Zero-Shot OOD CSIC Accuracy (Higher is Better)
bars2 = axes[1].bar(models, ood_accs, color=colors, edgecolor=edge_colors, linewidth=1.5, zorder=3)
axes[1].set_title('(b) Zero-Shot OOD Accuracy', fontweight='bold', pad=10)
axes[1].set_ylabel('Accuracy on CSIC 2010 (%)', fontweight='bold')
axes[1].set_ylim(88.0, 95.5)
axes[1].grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
for i, bar in enumerate(bars2):
    h = bar.get_height()
    prefix = 'WIN: ' if i == 2 else ''
    color = '#065f46' if i == 2 else '#1e293b'
    axes[1].text(bar.get_x() + bar.get_width()/2., h + 0.25, f'{prefix}{h:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold', color=color)

# Panel 3: CPU Inference Latency (Lower is Better)
bars3 = axes[2].bar(models, latencies, color=['#cbd5e1', '#cbd5e1', '#34d399'], edgecolor=edge_colors, linewidth=1.5, zorder=3)
axes[2].set_title('(c) CPU Inference Latency', fontweight='bold', pad=10)
axes[2].set_ylabel('Latency per Request (ms)', fontweight='bold')
axes[2].set_ylim(0, 3.0)
axes[2].axhline(2.0, color='#ef4444', linestyle='--', linewidth=1.2, label='WAF Limit (2.0 ms)')
axes[2].grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
for i, bar in enumerate(bars3):
    h = bar.get_height()
    prefix = 'FAST: ' if i == 2 else ''
    color = '#065f46' if i == 2 else '#1e293b'
    axes[2].text(bar.get_x() + bar.get_width()/2., h + 0.08, f'{prefix}{h:.2f} ms', ha='center', va='bottom', fontsize=9, fontweight='bold', color=color)

# Panel 4: Model Parameters (Lower is Better)
bars4 = axes[3].bar(models, params_k, color=['#cbd5e1', '#cbd5e1', '#34d399'], edgecolor=edge_colors, linewidth=1.5, zorder=3)
axes[3].set_title('(d) Total Parameter Scale', fontweight='bold', pad=10)
axes[3].set_ylabel('Parameters (Thousands, k)', fontweight='bold')
axes[3].set_ylim(0, 1400)
axes[3].grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
for i, bar in enumerate(bars4):
    h = bar.get_height()
    prefix = 'LIGHT: ' if i == 2 else ''
    color = '#065f46' if i == 2 else '#1e293b'
    axes[3].text(bar.get_x() + bar.get_width()/2., h + 35, f'{prefix}{h:.1f}k', ha='center', va='bottom', fontsize=9, fontweight='bold', color=color)

# Prominent Super-Title and Highlight Callout
fig.suptitle('Stage 3 Neural Foundation Tournament: Selecting the Optimal Anchor W_base (N = 418,540)', fontweight='bold', fontsize=14, y=0.98)

plt.tight_layout()
plt.subplots_adjust(top=0.86)

fig_path = os.path.join(FIG_DIR, "fig_d10_foundation_tournament_highlight.png")
plt.savefig(fig_path, dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d10_foundation_tournament_highlight.png"), dpi=300, bbox_inches='tight')
plt.close()

print(f"Generated: {fig_path}")
