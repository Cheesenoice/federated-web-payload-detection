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
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'figure.titlesize': 15
})

fig, ax = plt.subplots(figsize=(12, 7.0), dpi=300)

models = [
    'Client 1 (E-Commerce Silo)',
    'Client 2 (Retail Marketplace Silo)',
    'Client 3 (Commercial Bank Silo)',
    'Client 4 (FinTech Gateway Silo)',
    'Client 5 (Cloud Storage Silo)',
    'Client 6 (Enterprise Gov Silo)',
    'Pre-FL Foundation Anchor (W_base)',
    'Non-FL Centralized Oracle (W_cen)',
    'Post-FL Standard FedAvg Consensus',
    'Post-FL DAFL Consensus (Ours)'
]

cols = [
    'Benign Specificity\n(Anti-False Alarm Rate)',
    'XSS Defense Recall\n(2,267 Real Exploits)',
    'SQLi Defense Recall\n(912 Real Exploits)',
    'PathTrav Defense Recall\n(1,250 Real Exploits)'
]

# Matrix metrics [Benign Spec %, XSS Recall %, SQLi Recall %, PathTrav Recall %]
matrix = np.array([
    [97.96, 88.00, 60.86, 90.88],  # C1
    [98.21, 92.94, 68.42, 86.56],  # C2
    [92.57, 80.72, 90.02, 89.20],  # C3
    [97.79, 86.20, 93.10, 88.40],  # C4
    [86.18, 93.21, 61.07, 98.40],  # C5
    [93.35, 91.50, 78.40, 95.20],  # C6
    [85.22, 96.40, 78.40, 91.20],  # Anchor
    [81.97, 87.91, 90.68, 92.40],  # Centralized
    [95.13, 82.84, 77.41, 88.64],  # FedAvg
    [95.91, 92.19, 85.53, 91.92]   # DAFL
])

im = ax.imshow(matrix, cmap='RdYlGn', vmin=60, vmax=99, aspect='auto')

ax.set_xticks(range(len(cols)))
ax.set_xticklabels(cols, fontweight='bold', fontsize=11)
ax.set_yticks(range(len(models)))
ax.set_yticklabels(models, fontweight='bold', fontsize=10.5)

for i in range(len(models)):
    for j in range(len(cols)):
        val = matrix[i, j]
        color = 'white' if (val < 72 or val > 93) else '#0f172a'
        weight = 'bold' if (val < 70 or 'DAFL' in models[i]) else 'medium'
        txt = f'{val:.1f}%'
        if val < 70:
            txt += '\n[FATAL FAIL]'
        elif val < 82 and j == 0:
            txt += '\n[PANIC FA]'
        elif 'DAFL' in models[i]:
            txt += '\n[SAFE]'
        ax.text(j, i, txt, ha='center', va='center', color=color, fontweight=weight, fontsize=9.2)

# Highlight DAFL row with an emerald green border
rect = plt.Rectangle((-0.49, 8.51), 3.98, 0.98, fill=False, edgecolor='#047857', linewidth=3.2, linestyle='-')
ax.add_patch(rect)

# Highlight E-commerce SQLi failure
rect_c1 = plt.Rectangle((1.51, -0.48), 0.98, 1.96, fill=False, edgecolor='#b91c1c', linewidth=2.4, linestyle='--')
ax.add_patch(rect_c1)

# Highlight Centralized & C5 Benign false alarm crisis
rect_cen = plt.Rectangle((-0.48, 6.52), 0.96, 1.94, fill=False, edgecolor='#ea580c', linewidth=2.4, linestyle='--')
ax.add_patch(rect_cen)

ax.set_title('Per-Class Threat Defense Matrix on Gold OOD Benchmark (N = 17,139)\nRevealing Sector-Specific Blind Spots and Centralized False Alarm Crisis', 
             fontweight='bold', fontsize=13.5, pad=16)

cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
cbar.set_label('Detection Recall / Benign Specificity (%)', fontweight='bold', fontsize=10.5)

plt.tight_layout()

out1 = os.path.join(FIG_DIR, "fig_d22_client_silos_vs_ood_benchmark.png")
out2 = os.path.join(PUB_FIG_DIR, "fig_d22_client_silos_vs_ood_benchmark.png")
plt.savefig(out1, dpi=300, bbox_inches='tight')
plt.savefig(out2, dpi=300, bbox_inches='tight')
plt.close()
print(f"Generated clean Figure D22 Heatmap: {out1}")
