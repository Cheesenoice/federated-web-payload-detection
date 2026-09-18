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

# Top-tier academic styling
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 11.5,
    'ytick.labelsize': 10.5,
    'legend.fontsize': 10.5,
    'figure.titlesize': 14.5
})

# Create figure with ample headroom for title and legend
fig, ax = plt.subplots(figsize=(14, 7.2), dpi=300)

domains = [
    'Evaluation on E-Commerce Domain\n(Clients 1-2 Test Holdouts)',
    'Evaluation on Banking Domain\n(Clients 3-4 Test Holdouts)',
    'Evaluation on Cloud SaaS Domain\n(Clients 5-6 Test Holdouts)'
]

# F1-Scores (%)
m1_f1 = [99.80, 38.41, 41.20]  # E-Com model
m3_f1 = [36.12, 99.74, 43.50]  # Banking model
m5_f1 = [39.80, 42.10, 99.85]  # Cloud model
fed_f1 = [99.78, 99.74, 99.82] # Federated Global Consensus

x = np.arange(len(domains))
width = 0.19

# Plot bars with modern contrasting colors
rects1 = ax.bar(x - 1.5*width, m1_f1, width, label='Isolated Model 1 (Trained on E-Com XSS)', color='#60a5fa', edgecolor='#1e40af', linewidth=1.2, zorder=3)
rects2 = ax.bar(x - 0.5*width, m3_f1, width, label='Isolated Model 3 (Trained on Banking SQLi)', color='#fbbf24', edgecolor='#b45309', linewidth=1.2, zorder=3)
rects3 = ax.bar(x + 0.5*width, m5_f1, width, label='Isolated Model 5 (Trained on Cloud PathTrav)', color='#c084fc', edgecolor='#6b21a8', linewidth=1.2, zorder=3)
rects4 = ax.bar(x + 1.5*width, fed_f1, width, label='Federated Global Consensus (Our System - Resilient)', color='#10b981', edgecolor='#064e3b', linewidth=2.2, hatch='///', zorder=3)

# Shaded Vulnerability Zone (F1 < 50%)
ax.axhspan(0, 50, color='#fee2e2', alpha=0.5, zorder=1)
ax.axhline(50, color='#ef4444', linestyle='--', linewidth=1.8, zorder=2)

# Label the threshold on the right without colliding with bar text
ax.text(2.45, 52, '--- CRITICAL VULNERABILITY THRESHOLD (50% F1) ---', color='#991b1b', fontweight='bold', fontsize=10, ha='right', va='bottom', zorder=4)

# Value annotations on top of bars
def autolabel(rects, is_fed=False):
    for rect in rects:
        height = rect.get_height()
        if height < 50:
            color = '#b91c1c'
            bg_color = '#fef2f2'
            edge_color = '#fca5a5'
            label_text = f'{height:.1f}%\n(VULN)'
            y_pos = height + 1.8
        else:
            color = '#065f46' if is_fed else '#1e293b'
            bg_color = '#ecfdf5' if is_fed else '#f8fafc'
            edge_color = '#6ee7b7' if is_fed else '#cbd5e1'
            label_text = f'{height:.1f}%\n(OK)' if is_fed else f'{height:.1f}%'
            y_pos = height + 1.8
            
        ax.text(rect.get_x() + rect.get_width()/2.0, y_pos, label_text,
                ha='center', va='bottom', fontsize=9, fontweight='bold', color=color,
                bbox=dict(boxstyle='round,pad=0.25', facecolor=bg_color, edgecolor=edge_color, linewidth=0.8, alpha=0.95),
                zorder=5)

autolabel(rects1)
autolabel(rects2)
autolabel(rects3)
autolabel(rects4, is_fed=True)

# Formatting
ax.set_ylabel('Cross-Domain Detection Macro F1-Score (%)', fontweight='bold', labelpad=10)
ax.set_xticks(x)
ax.set_xticklabels(domains, fontweight='bold')
ax.set_ylim(0, 120)
ax.set_yticks([0, 20, 40, 50, 60, 80, 100])
ax.grid(axis='y', linestyle='--', alpha=0.45, zorder=0)

# Clean figure title at the very top
fig.suptitle('Empirical Proof of Catastrophic Domain Collapse: Isolated Silos vs. Federated Consensus (Table 3)', fontweight='bold', fontsize=14, y=0.98)

# Legend positioned cleanly BELOW the title and ABOVE the plot with dedicated margin
ax.legend(
    loc='lower center',
    bbox_to_anchor=(0.5, 1.02),
    ncol=2,
    frameon=True,
    framealpha=0.98,
    edgecolor='#cbd5e1',
    fancybox=True
)

# Manually adjust subplots to guarantee zero collision
plt.subplots_adjust(top=0.84, bottom=0.12, left=0.08, right=0.96)

fig_path = os.path.join(FIG_DIR, "fig_d5_cross_domain_vulnerability_highlight.png")
plt.savefig(fig_path, dpi=300)
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d5_cross_domain_vulnerability_highlight.png"), dpi=300)
plt.close()

print(f"Successfully generated perfect layout chart to: {fig_path}")
