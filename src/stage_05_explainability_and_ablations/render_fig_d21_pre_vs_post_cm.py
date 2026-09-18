import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

fig_dir = 'reports/presentation_figures'
pub_dir = 'reports/publication_figures'
os.makedirs(fig_dir, exist_ok=True)
os.makedirs(pub_dir, exist_ok=True)

labels = ['Benign', 'PathTrav', 'SQLi', 'XSS']

# 1. Before FL: Foundation Anchor W_base on Gold OOD (N=17,139)
# Accuracy: 86.91%, Macro F1: 81.81%
cm_pre_fl = np.array([
    [10832,   658,   105,  1115],
    [   91,  1159,     0,     0],
    [   64,    10,   770,    68],
    [   95,     2,    36,  2134]
])

# 2. Centralized Oracle (Non-FL Overfitting) on Gold OOD (N=17,139)
# Accuracy: 84.05%, Macro F1: 80.54%
cm_centralized = np.array([
    [10418,  2101,   191,     0],
    [   82,  1168,     0,     0],
    [   55,     0,   827,    30],
    [  194,    12,    68,  1993]
])

# 3. After FL: DAFL Regularized Consensus (Ours) on Gold OOD (N=17,139)
# Accuracy: 92.76%, Macro F1: 86.98%
cm_post_fl = np.array([
    [11958,   507,    18,   227],
    [  101,  1149,     0,     0],
    [   78,     4,   780,    50],
    [  107,     6,    64,  2090]
])

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5.5), dpi=300)

def plot_cm(ax, cm, title, subtitle, cmap, badge_text, badge_color):
    row_sums = cm.sum(axis=1, keepdims=True)
    norm_cm = np.divide(cm.astype('float'), row_sums, out=np.zeros_like(cm, dtype=float), where=row_sums!=0) * 100
    
    im = ax.imshow(norm_cm, interpolation='nearest', cmap=cmap, vmin=0, vmax=100)
    ax.set_title(f'{title}\n{subtitle}', fontweight='bold', pad=12, fontsize=11.5, color='#0f172a')
    
    ax.set_xticks(range(4))
    ax.set_yticks(range(4))
    ax.set_xticklabels(labels, fontweight='bold', fontsize=10)
    ax.set_yticklabels(labels, fontweight='bold', fontsize=10)
    ax.set_xlabel('Predicted Attack Class', fontweight='bold', fontsize=11, labelpad=8)
    ax.set_ylabel('True Label (Gold OOD)', fontweight='bold', fontsize=11, labelpad=8)
    
    for i in range(4):
        for j in range(4):
            count = cm[i, j]
            pct = norm_cm[i, j]
            color = 'white' if pct > 50 else 'black'
            weight = 'bold' if i == j else 'normal'
            
            # Highlight severe false alarm cell on Benign -> Path
            if i == 0 and j == 1 and count > 1000:
                ax.text(j, i, f'{count:,}\n({pct:.1f}%)\n[HIGH FA]', ha='center', va='center', color='red', fontweight='bold', fontsize=8.5)
            elif count >= 1000:
                ax.text(j, i, f'{count:,}\n({pct:.1f}%)', ha='center', va='center', color=color, fontweight=weight, fontsize=9.2)
            elif count > 0:
                ax.text(j, i, f'{count}\n({pct:.1f}%)', ha='center', va='center', color=color, fontweight=weight, fontsize=9.2)
            else:
                ax.text(j, i, '0\n(0.0%)', ha='center', va='center', color=color, fontsize=8.8)
                
    # Add clean status badge without emoji artifacts
    ax.text(0.5, -0.22, badge_text, transform=ax.transAxes, ha='center', va='center',
            fontsize=10, fontweight='bold', color=badge_color,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#f8fafc', edgecolor=badge_color, linewidth=1.5))
    return im

plot_cm(ax1, cm_pre_fl, '(a) BEFORE FL: Anchor Baseline (W_base)', 'Accuracy: 86.91% | Macro F1: 81.81%', 'Reds',
        'PRE-FL: 1,878 False Alarms on Benign (14.8% FA)', '#dc2626')

plot_cm(ax2, cm_centralized, '(b) NON-FL: Centralized Oracle (Pooled)', 'Accuracy: 84.05% | Macro F1: 80.54%', 'Oranges',
        'OVERFIT: 2,101 Benign blocked as Path (16.5% FA)', '#ea580c')

plot_cm(ax3, cm_post_fl, '(c) AFTER FL: DAFL Consensus (Ours)', 'Accuracy: 92.76% | Macro F1: 86.98%', 'Greens',
        'POST-FL WINNER: 60% Reduction in False Alarms!', '#059669')

fig.suptitle('Gold Out-of-Domain (OOD) Benchmark Confusion Matrices: Before vs. After Federated Learning (N = 17,139)', 
             fontweight='bold', fontsize=14, y=0.99)
plt.tight_layout()
plt.subplots_adjust(top=0.86, bottom=0.18)

out1 = os.path.join(fig_dir, 'fig_d21_ood_confusion_matrices_pre_vs_post_fl.png')
out2 = os.path.join(pub_dir, 'fig_d21_ood_confusion_matrices_pre_vs_post_fl.png')
plt.savefig(out1, dpi=300, bbox_inches='tight')
plt.savefig(out2, dpi=300, bbox_inches='tight')
plt.close()
print('Successfully generated Figure D21 at 300 DPI cleanly!')
