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

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10.5,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'figure.titlesize': 14.5
})

# =========================================================================
# FIGURE D11: HTTP REQUEST ANATOMY & REGULATORY PRIVACY COMPLIANCE MATRIX
# =========================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.8), dpi=300, gridspec_kw={'width_ratios': [1.1, 0.9]})

# Left Panel: HTTP Request Anatomy & PII Entanglement
ax1.set_xlim(0, 10)
ax1.set_ylim(0, 10)
ax1.axis('off')
ax1.set_title('(a) HTTP Request Anatomy & PII Entanglement', fontweight='bold', fontsize=12, pad=12)

# Box for Raw HTTP Request
rect_http = patches.FancyBboxPatch((0.3, 0.5), 9.4, 8.8, boxstyle="round,pad=0.2", ec="#334155", fc="#f8fafc", lw=1.5)
ax1.add_patch(rect_http)

# Request Line
ax1.text(0.6, 8.6, "POST /api/v2/checkout/pay?ref=ecom_984 HTTP/1.1", fontfamily='monospace', fontsize=10, fontweight='bold', color="#0f172a")
ax1.text(0.6, 8.1, "Host: secure.enterprise-bank.com", fontfamily='monospace', fontsize=9.5, color="#334155")
ax1.text(0.6, 7.6, "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)", fontfamily='monospace', fontsize=9.5, color="#64748b")

# Highlight Cookie / Auth Header (PII)
rect_pii1 = patches.FancyBboxPatch((0.5, 6.4), 9.0, 0.9, boxstyle="round,pad=0.1", ec="#ef4444", fc="#fee2e2", lw=1.2)
ax1.add_patch(rect_pii1)
ax1.text(0.7, 6.9, "Cookie: session_id=e8f9a2b4; user_jwt=eyJhbGciOi... [PII / SENSITIVE]", fontfamily='monospace', fontsize=9.5, fontweight='bold', color="#991b1b")
ax1.text(0.7, 6.55, "Authorization: Bearer sk_live_9948274018247012 [SECRET API KEY]", fontfamily='monospace', fontsize=9.5, fontweight='bold', color="#991b1b")

# Content Type & Length
ax1.text(0.6, 5.8, "Content-Type: application/json; charset=utf-8", fontfamily='monospace', fontsize=9.5, color="#334155")

# Body with Entangled Exploit & Customer Data
rect_pii2 = patches.FancyBboxPatch((0.5, 1.2), 9.0, 4.2, boxstyle="round,pad=0.1", ec="#dc2626", fc="#fef2f2", lw=1.2)
ax1.add_patch(rect_pii2)

body_text = """{
  "customer_name": "Nguyen Van A",          <-- GDPR Art. 4 PII
  "credit_card": "4532-0159-8834-1120",       <-- PCI-DSS Req. 3.4
  "billing_address": "123 Tech Ave, Bangkok", <-- HIPAA / CCPA
  "search_filter": "' UNION SELECT credit_card, cvv FROM users--"
}"""
ax1.text(0.7, 4.7, "POST Body (JSON Payload):", fontsize=9.5, fontweight='bold', color="#991b1b")
ax1.text(0.7, 1.5, body_text, fontfamily='monospace', fontsize=9, color="#7f1d1d")

# Callout banner at bottom
ax1.text(5.0, 0.8, "CRITICAL: Exploit is inextricably entangled with customer PII!", ha='center', fontsize=9.5, fontweight='bold', color="#b91c1c")

# Right Panel: Regulatory Compliance Matrix
ax2.set_xlim(0, 10)
ax2.set_ylim(0, 10)
ax2.axis('off')
ax2.set_title('(b) Global Data Privacy Compliance Matrix', fontweight='bold', fontsize=12, pad=12)

regulations = [
    {"name": "EU GDPR (General Data Protection Reg.)", "rule": "Art. 4 (PII), Art. 9 (Special Categories)\nArt. 83: Up to €20M or 4% Global Turnover", "status": "CENTRALIZED: ILLEGAL [FAIL]\nFEDERATED: 100% COMPLIANT [PASS]", "color": "#eff6ff", "border": "#2563eb"},
    {"name": "PCI-DSS v4.0 (Payment Card Security)", "rule": "Requirement 3.4 & 4.1: Render PAN unreadable\nProhibits transmission of cleartext card data", "status": "CENTRALIZED: VIOLATION [FAIL]\nFEDERATED: ZERO RAW LOGS [PASS]", "color": "#fef2f2", "border": "#dc2626"},
    {"name": "HIPAA & CCPA / CPRA", "rule": "45 CFR § 164.312 & Cal. Civ. Code § 1798\nStrict healthcare & consumer privacy audit", "status": "CENTRALIZED: PROHIBITED [FAIL]\nFEDERATED: FULL PRIVACY [PASS]", "color": "#f0fdf4", "border": "#16a34a"}
]

y_pos = [6.8, 3.8, 0.8]
for i, reg in enumerate(regulations):
    box = patches.FancyBboxPatch((0.2, y_pos[i]), 9.6, 2.5, boxstyle="round,pad=0.15", ec=reg["border"], fc=reg["color"], lw=1.3)
    ax2.add_patch(box)
    ax2.text(0.5, y_pos[i] + 1.9, reg["name"], fontsize=10, fontweight='bold', color="#0f172a")
    ax2.text(0.5, y_pos[i] + 1.1, reg["rule"], fontsize=8.8, color="#334155")
    ax2.text(9.5, y_pos[i] + 1.2, reg["status"], fontsize=8.8, fontweight='bold', ha='right', color="#1e293b")

fig.suptitle('The Regulatory Barrier: Why Centralized Log Pooling is Impossible in Multi-Tenant WAFs', fontweight='bold', fontsize=13.5, y=0.98)
plt.tight_layout()
plt.subplots_adjust(top=0.88)

fig_d11_path = os.path.join(FIG_DIR, "fig_d11_regulatory_compliance_matrix.png")
plt.savefig(fig_d11_path, dpi=300)
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d11_regulatory_compliance_matrix.png"), dpi=300)
plt.close()
print(f"Generated: {fig_d11_path}")


# =========================================================================
# FIGURE D12: 4 RESEARCH GAPS & LIMITATIONS TAXONOMY
# =========================================================================
fig, ax = plt.subplots(figsize=(14, 5.4), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')
ax.set_title('Four Critical Research Gaps in Collaborative Web Attack Detection', fontweight='bold', fontsize=13.5, pad=15)

gaps = [
    {"num": "GAP 1", "title": "Multi-Tenant Data Silos", "desc": "80B+ attacks/yr, but enterprises cannot share raw HTTP logs due to strict GDPR/PCI-DSS.", "impact": "Domain Blindness (< 44% F1)", "color": "#fee2e2", "border": "#dc2626"},
    {"num": "GAP 2", "title": "Extreme Non-IID Skew", "desc": "E-Commerce sees 60% XSS, Banking sees 60% SQLi. Local gradients drift apart violently.", "impact": "||w_k - w_j|| Weight Divergence", "color": "#fef3c7", "border": "#d97706"},
    {"num": "GAP 3", "title": "Zero-Shot OOD Collapse", "desc": "Centralized DL achieves 99.97% in-domain but collapses to 58.61% on external CSIC 2010.", "impact": "Generalization Paradox (-41%)", "color": "#eff6ff", "border": "#2563eb"},
    {"num": "GAP 4", "title": "Line-Rate Latency Barrier", "desc": "SecBERT takes 42.5 ms/req, violating real-time WAF SLA limits (< 2.0 ms on edge gateways).", "impact": "59x Too Slow for Production", "color": "#f3e8ff", "border": "#7c3aed"}
]

col_w = 2.25
spacing = 0.2
left_margin = 0.2

for i, g in enumerate(gaps):
    x = left_margin + i * (col_w + spacing)
    card = patches.FancyBboxPatch((x, 0.5), col_w, 8.5, boxstyle="round,pad=0.15", ec=g["border"], fc=g["color"], lw=1.5)
    ax.add_patch(card)
    
    # Badge
    badge = patches.FancyBboxPatch((x + 0.2, 7.8), col_w - 0.4, 0.9, boxstyle="round,pad=0.1", ec=g["border"], fc=g["border"], lw=1.0)
    ax.add_patch(badge)
    ax.text(x + col_w/2.0, 8.25, g["num"], ha='center', va='center', color="#ffffff", fontweight='bold', fontsize=11)
    
    # Title
    ax.text(x + col_w/2.0, 7.2, g["title"], ha='center', va='center', color="#0f172a", fontweight='bold', fontsize=10.5)
    
    # Description
    desc_lines = g["desc"].split(". ")
    y_text = 6.2
    for line in desc_lines:
        ax.text(x + 0.15, y_text, line.strip(), fontsize=9, color="#334155", wrap=True)
        y_text -= 1.1
        
    # Impact Box
    impact_box = patches.FancyBboxPatch((x + 0.15, 0.8), col_w - 0.3, 1.3, boxstyle="round,pad=0.08", ec=g["border"], fc="#ffffff", lw=1.1)
    ax.add_patch(impact_box)
    ax.text(x + col_w/2.0, 1.45, "FATAL IMPACT:", ha='center', fontsize=8.5, fontweight='bold', color=g["border"])
    ax.text(x + col_w/2.0, 1.05, g["impact"], ha='center', fontsize=8.5, fontweight='bold', color="#0f172a")

plt.tight_layout()
fig_d12_path = os.path.join(FIG_DIR, "fig_d12_research_gaps_taxonomy.png")
plt.savefig(fig_d12_path, dpi=300)
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d12_research_gaps_taxonomy.png"), dpi=300)
plt.close()
print(f"Generated: {fig_d12_path}")
