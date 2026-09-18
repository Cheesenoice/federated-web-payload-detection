import os
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIG_DIR = os.path.join(ROOT_DIR, "reports", "presentation_figures")
PUB_FIG_DIR = os.path.join(ROOT_DIR, "reports", "publication_figures")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(PUB_FIG_DIR, exist_ok=True)

# Top-tier academic publication styling
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10.5,
    'figure.titlesize': 15
})

# =========================================================================
# FIGURE D12: 4 RESEARCH GAPS TAXONOMY (POLISHED & BALANCED TYPOGRAPHY)
# =========================================================================
fig, axes = plt.subplots(1, 4, figsize=(16.5, 5.5), dpi=300)

gaps = [
    {
        "badge": "GAP 1: PRIVACY WALL",
        "title": "Multi-Tenant Data Silos",
        "bullets": [
            "• 80B+ web attacks annually across global enterprise infra.",
            "• HTTP logs contain user PII, JWT tokens & credit cards.",
            "• Strict GDPR & PCI-DSS laws make log pooling illegal."
        ],
        "impact_label": "FATAL VULNERABILITY",
        "impact": "Cross-Domain Blindness\n(F1 collapses to < 40%)",
        "bg_color": "#fef2f2",
        "border_color": "#ef4444",
        "header_color": "#dc2626"
    },
    {
        "badge": "GAP 2: DISTRIBUTION SKEW",
        "title": "Extreme Non-IID Skew",
        "bullets": [
            "• E-Commerce sees 60%+ XSS.",
            "• Banking sees 60%+ SQLi.",
            "• Cloud SaaS sees 60%+ Traversal.",
            "• Local gradients diverge violently: ||w_k - w_j|| >> 0."
        ],
        "impact_label": "FATAL VULNERABILITY",
        "impact": "Severe Client Drift\n& Optimization Collapse",
        "bg_color": "#fffbeb",
        "border_color": "#f59e0b",
        "header_color": "#d97706"
    },
    {
        "badge": "GAP 3: ZERO-DAY COLLAPSE",
        "title": "Zero-Shot OOD Failure",
        "bullets": [
            "• Centralized models overfit internal dataset distribution.",
            "• 99.97% in-domain accuracy.",
            "• Collapses to 58.61% accuracy on unseen CSIC 2010 zero-days."
        ],
        "impact_label": "FATAL VULNERABILITY",
        "impact": "Generalization Paradox\n(-41.36% Accuracy Drop)",
        "bg_color": "#eff6ff",
        "border_color": "#3b82f6",
        "header_color": "#2563eb"
    },
    {
        "badge": "GAP 4: LATENCY BARRIER",
        "title": "Line-Rate WAF Limit",
        "bullets": [
            "• Heavy NLP models (SecBERT) require 42.5 ms per payload.",
            "• Exceeds real-time edge SLA limit (< 2.0 ms) by 21x.",
            "• 418 MB memory is too heavy for Gateway Envoy sidecars."
        ],
        "impact_label": "FATAL VULNERABILITY",
        "impact": "59x Too Slow for\nWire-Speed Production WAF",
        "bg_color": "#f5f3ff",
        "border_color": "#8b5cf6",
        "header_color": "#7c3aed"
    }
]

for i, (ax, g) in enumerate(zip(axes, gaps)):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Outer Card Background
    card = patches.FancyBboxPatch(
        (0.15, 0.15), 9.7, 9.7,
        boxstyle="round,pad=0.2,rounding_size=0.4",
        ec=g["border_color"], fc=g["bg_color"], lw=1.8
    )
    ax.add_patch(card)
    
    # Top Header Badge
    badge = patches.FancyBboxPatch(
        (0.6, 8.45), 8.8, 0.95,
        boxstyle="round,pad=0.15,rounding_size=0.2",
        ec=g["header_color"], fc=g["header_color"], lw=1.0
    )
    ax.add_patch(badge)
    ax.text(5.0, 8.92, g["badge"], ha='center', va='center', color="#ffffff", fontweight='bold', fontsize=10.2)
    
    # Card Main Title
    ax.text(5.0, 7.75, g["title"], ha='center', va='center', color="#0f172a", fontweight='bold', fontsize=12.8)
    
    # Bullet points with wrapped text
    y_cursor = 7.0
    for bullet in g["bullets"]:
        wrapped = textwrap.fill(bullet, width=31)
        num_lines = wrapped.count('\n') + 1
        ax.text(0.6, y_cursor, wrapped, ha='left', va='top', color="#334155", fontsize=9.4, linespacing=1.28)
        y_cursor -= (0.42 * num_lines + 0.22)
        
    # Bottom Consequence / Impact Banner
    impact_box = patches.FancyBboxPatch(
        (0.55, 0.55), 8.9, 1.9,
        boxstyle="round,pad=0.15,rounding_size=0.25",
        ec=g["border_color"], fc="#ffffff", lw=1.3
    )
    ax.add_patch(impact_box)
    
    ax.text(5.0, 1.98, g["impact_label"], ha='center', va='center', color=g["header_color"], fontweight='bold', fontsize=8.8)
    ax.text(5.0, 1.20, g["impact"], ha='center', va='center', color="#0f172a", fontweight='bold', fontsize=9.3, linespacing=1.15)

fig.suptitle('Four Critical Research Gaps in Modern Collaborative Web Attack Defense', fontweight='bold', fontsize=14.5, y=0.98)
plt.tight_layout()
plt.subplots_adjust(top=0.88)

fig_d12_path = os.path.join(FIG_DIR, "fig_d12_research_gaps_taxonomy.png")
plt.savefig(fig_d12_path, dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d12_research_gaps_taxonomy.png"), dpi=300, bbox_inches='tight')
plt.close()
print(f"Polished Figure D12 generated at: {fig_d12_path}")
