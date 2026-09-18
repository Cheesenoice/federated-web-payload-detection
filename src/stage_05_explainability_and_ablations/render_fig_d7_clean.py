import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIG_DIR = os.path.join(ROOT_DIR, "reports", "presentation_figures")
PUB_FIG_DIR = os.path.join(ROOT_DIR, "reports", "publication_figures")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(PUB_FIG_DIR, exist_ok=True)

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10.5,
    'axes.labelsize': 11.5,
    'axes.titlesize': 13,
    'xtick.labelsize': 10.5,
    'ytick.labelsize': 10.5,
    'legend.fontsize': 10
})

fig, ax = plt.subplots(figsize=(13, 6.2), dpi=300)

models_data = [
    {
        "name": "SecBERT (Heavy Transformer)",
        "params": "110M params",
        "latency": 42.50,
        "size": 418.0,
        "color": "#ef4444",
        "text_pos": (27.0, 260.0),
        "status": "[FAIL] 59x Too Slow for WAF"
    },
    {
        "name": "DistilBERT (Distilled Transformer)",
        "params": "66M params",
        "latency": 24.10,
        "size": 256.0,
        "color": "#f97316",
        "text_pos": (12.0, 110.0),
        "status": "[FAIL] High Latency Overhead"
    },
    {
        "name": "CharCNN (1D ConvNet)",
        "params": "1.2M params",
        "latency": 1.82,
        "size": 4.80,
        "color": "#3b82f6",
        "text_pos": (7.5, 25.0),
        "status": "[WARN] Marginally Acceptable"
    },
    {
        "name": "Bi-LSTM + Attention (RNN)",
        "params": "448k params",
        "latency": 2.41,
        "size": 1.80,
        "color": "#8b5cf6",
        "text_pos": (9.0, 4.5),
        "status": "[WARN] Sequential Bottleneck"
    },
    {
        "name": "Transformer Net (Ours)",
        "params": "156k params (3 Layers)",
        "latency": 0.72,
        "size": 0.63,
        "color": "#10b981",
        "text_pos": (5.5, 0.45),
        "status": "[PASS] 100% Line-Rate Compliant"
    }
]

# Wire-Speed Edge Feasible Zone
ax.axvspan(0, 2.0, color='#ecfdf5', alpha=0.75, label='Wire-Speed Edge Feasible Zone (< 2.0 ms)', zorder=1)
ax.axvline(2.0, color='#dc2626', linestyle='--', linewidth=1.8, label='Real-Time WAF SLA Limit (2.0 ms/req)', zorder=2)

# Scatter Bubbles
for item in models_data:
    lat = item["latency"]
    sz = item["size"]
    bubble_sz = sz * 2.8 + 240
    
    ax.scatter(lat, sz, s=bubble_sz, color=item["color"], alpha=0.88, edgecolors='#0f172a', linewidth=1.6, zorder=4)
    
    # Text Annotation Box
    box_ec = "#10b981" if "Ours" in item["name"] else "#cbd5e1"
    box_fc = "#f0fdf4" if "Ours" in item["name"] else "#ffffff"
    box_lw = 1.6 if "Ours" in item["name"] else 1.0
    
    label_text = f"<b>{item['name']}</b>\n{item['params']} | {sz:.2f} MB\nLatency: <b>{lat:.2f} ms/req</b>\n{item['status']}"
    # Replace <b> tags for matplotlib
    clean_text = f"{item['name']}\n{item['params']} | {sz:.2f} MB\nLatency: {lat:.2f} ms/req\n{item['status']}"
    
    ax.annotate(
        clean_text,
        xy=(lat, sz),
        xytext=item["text_pos"],
        fontsize=9.2,
        fontweight='medium',
        arrowprops=dict(arrowstyle="->", color="#334155", lw=1.2, shrinkA=3, shrinkB=6),
        bbox=dict(boxstyle="round,pad=0.4,rounding_size=0.3", fc=box_fc, ec=box_ec, lw=box_lw),
        zorder=5
    )

ax.set_yscale('log')
ax.set_xlabel('CPU Inference Latency per Payload (ms) [Lower is Better]', fontweight='bold', fontsize=11.5)
ax.set_ylabel('Model Memory Footprint (MB, Log Scale) [Lower is Better]', fontweight='bold', fontsize=11.5)
ax.set_title('Edge Deployability Frontier: Inference Latency vs. Memory Footprint on Commodity CPU', fontweight='bold', fontsize=13.5, pad=15)

ax.set_xlim(0, 48)
ax.set_ylim(0.18, 900)
ax.grid(True, which='both', linestyle='--', alpha=0.45, zorder=0)
ax.legend(loc='upper left', framealpha=0.95, facecolor='#ffffff', edgecolor='#94a3b8', fontsize=10)

plt.tight_layout()

fig_d7_path = os.path.join(FIG_DIR, "fig_d7_edge_latency_tradeoff.png")
plt.savefig(fig_d7_path, dpi=300, bbox_inches='tight')
plt.savefig(os.path.join(PUB_FIG_DIR, "fig_d7_edge_latency_tradeoff.png"), dpi=300, bbox_inches='tight')
plt.close()
print(f"Generated clean Figure D7: {fig_d7_path}")
