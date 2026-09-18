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
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.titlesize': 14
})

labels = ['Benign', 'PathTrav', 'SQLi', 'XSS']

# 1. In-Domain Test B (N=354,808) - DAFL Consensus
cm_test_b = np.array([
    [263246,     79,    227,     57],
    [    36,   1991,      0,      0],
    [   164,      2,   9753,      9],
    [    13,      0,      0,  79231]
])

# 2. Gold-Standard Purified OOD (N=14,430) - Centralized Oracle (Overfit Non-FL)
cm_ood_cent = np.array([
    [10924,  1682,   103,     1],
    [   25,   323,     0,     0],
    [   13,     0,   497,    13],
    [  234,     7,     6,   602]
])

# 3. Gold-Standard Purified OOD (N=14,430) - DAFL (Ours Winner)
cm_ood_dafl = np.array([
    [11958,   507,    18,   227],
    [   24,   324,     0,     0],
    [   10,     0,   486,    27],
    [  124,     0,    13,   712]
])

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5.2), dpi=300)

def plot_cm(ax, cm, title, subtitle, cmap, is_winner=False, is_centralized=False):
    row_sums = cm.sum(axis=1, keepdims=True)
    norm_cm = np.divide(cm.astype('float'), row_sums, out=np.zeros_like(cm, dtype=float), where=row_sums!=0) * 100
    
    im = ax.imshow(norm_cm, interpolation='nearest', cmap=cmap, vmin=0, vmax=100)
    title_color = "#065f46" if is_winner else ("#9a3412" if is_centralized else "#1e3a8a")
    ax.set_title(f"{title}\n{subtitle}", fontweight='bold', pad=10, color=title_color)
    
    ax.set_xticks(range(4))
    ax.set_yticks(range(4))
    ax.set_xticklabels(labels, fontweight='medium')
    ax.set_yticklabels(labels, fontweight='medium')
    ax.set_xlabel('Predicted Label', fontweight='bold')
    ax.set_ylabel('True Label', fontweight='bold')
    
    for i in range(4):
        for j in range(4):
            count = cm[i, j]
            pct = norm_cm[i, j]
            color = "white" if pct > 50 else "black"
            weight = 'bold' if i == j else 'normal'
            
            if is_centralized and i == 0 and j == 1:
                ax.text(j, i, f"{count:,}\n({pct:.1f}%)\n[HIGH FA]", ha="center", va="center", color="red", fontweight="bold", fontsize=8.2)
            elif count >= 1000:
                ax.text(j, i, f"{count:,}\n({pct:.1f}%)", ha="center", va="center", color=color, fontweight=weight, fontsize=8.8)
            elif count > 0:
                ax.text(j, i, f"{count}\n({pct:.1f}%)", ha="center", va="center", color=color, fontweight=weight, fontsize=8.8)
            else:
                ax.text(j, i, "0\n(0.0%)", ha="center", va="center", color=color, fontsize=8.5)
    return im

im1 = plot_cm(ax1, cm_test_b, "(a) In-Domain Test B (N=354,808)", "DAFL Consensus (Accuracy: 99.83% | F1: 98.74%)", "Blues")
im2 = plot_cm(ax2, cm_ood_cent, "(b) Purified OOD Benchmark (N=14,430)", "Centralized Oracle (Accuracy: 85.56% | F1: 72.25%)", "Oranges", is_centralized=True)
im3 = plot_cm(ax3, cm_ood_dafl, "(c) Purified OOD Benchmark (N=14,430)", "DAFL Regularization (Accuracy: 93.42% | F1: 80.80%)", "Greens", is_winner=True)

fig.suptitle('Empirical Confusion Matrices: In-Domain Precision vs. Purified Zero-Shot OOD Generalization', fontweight='bold', fontsize=14.5, y=0.98)
plt.tight_layout()
plt.subplots_adjust(top=0.86)

save_p1 = os.path.join(FIG_DIR, "fig_d15_confusion_matrices_audit.png")
save_p2 = os.path.join(PUB_FIG_DIR, "fig_d15_confusion_matrices_audit.png")
plt.savefig(save_p1, dpi=300, bbox_inches='tight')
plt.savefig(save_p2, dpi=300, bbox_inches='tight')
plt.close()
print(f"Successfully re-rendered Figure D15: {save_p1}")
