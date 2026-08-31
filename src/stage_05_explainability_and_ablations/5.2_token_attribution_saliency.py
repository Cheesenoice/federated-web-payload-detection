import os
import sys
import html
import logging
import importlib.util
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Dynamic import helper for Stage 3 modules
def dynamic_import(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

CURRENT_DIR = os.path.dirname(__file__)
STAGE_03_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "stage_03_neural_foundation"))

ds_mod = dynamic_import("dataset_tokenizer", os.path.join(STAGE_03_DIR, "3.1_dataset_and_char_tokenizer.py"))
arch_mod = dynamic_import("neural_archs", os.path.join(STAGE_03_DIR, "3.2_neural_architectures.py"))

encode_payload = ds_mod.encode_payload
LABEL_MAP = ds_mod.LABEL_MAP
INV_LABEL_MAP = ds_mod.INV_LABEL_MAP
TransformerEncoderNet = arch_mod.TransformerEncoderNet

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_04_federated_rep60k")
W_BASE_DIR = os.path.join(ROOT_DIR, "models", "stage_03_neural")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports", "stage_05_xai")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")

os.makedirs(FIGURES_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODELS_DIR, "W_fedavgm.pt")
if not os.path.exists(MODEL_PATH):
    MODEL_PATH = os.path.join(W_BASE_DIR, "W_base.pt")

PAYLOADS_FOR_SALIENCY = [
    ("XSS", "<script>alert('XSS_PAYLOAD')</script>"),
    ("XSS_Event", "<img src=1 onerror=alert(document.cookie)>"),
    ("SQL_Injection", "' UNION SELECT 1, null, password FROM users--"),
    ("SQL_AuthBypass", "admin' OR 1=1-- -"),
    ("Path_Traversal", "../../../../etc/shadow%00"),
    ("Path_Windows", "..\\..\\..\\windows\\system.ini"),
    ("Benign_Request", "/api/v1/search?query=web+security+machine+learning&limit=10")
]

def compute_input_saliency(model, text, device):
    """
    Computes exact gradient saliency vectors with respect to input token embeddings:
    Saliency(i) = || d(Logit_predicted) / d(Embedding_i) ||_2
    """
    tokens = encode_payload(text, max_len=256)
    x_tensor = torch.tensor(tokens, dtype=torch.long).unsqueeze(0).to(device)
    
    seq_len = x_tensor.size(1)
    padding_mask = (x_tensor == 0)
    
    # 1. Forward through embedding layer and retain grad
    token_emb = model.token_embedding(x_tensor) # [1, seq_len, embed_dim]
    pos_emb = model.pos_embedding[:, :seq_len, :]
    emb = token_emb + pos_emb
    emb.retain_grad()
    
    # 2. Forward through transformer encoder
    h = model.transformer_encoder(emb, src_key_padding_mask=padding_mask)
    mask = (~padding_mask).unsqueeze(-1).float()
    pooled = torch.sum(h * mask, dim=1) / torch.clamp(mask.sum(dim=1), min=1.0)
    pooled = model.ln(pooled)
    logits = model.fc(pooled)
    
    pred_idx = torch.argmax(logits, dim=1).item()
    target_logit = logits[0, pred_idx]
    
    # 3. Backward to compute gradient on embedding
    model.zero_grad()
    target_logit.backward()
    
    # Gradient magnitude: [seq_len]
    grad = emb.grad[0] # [seq_len, embed_dim]
    saliency = torch.norm(grad, dim=1).cpu().numpy()
    
    # Crop to active length
    active_len = min(len(text), 256)
    active_saliency = saliency[:active_len]
    
    # Normalize 0..1
    if active_saliency.max() > 0:
        active_saliency = active_saliency / active_saliency.max()
        
    return active_saliency, pred_idx, F.softmax(logits, dim=1)[0, pred_idx].item()

def generate_saliency_figure(results, save_path):
    """
    Plots a multi-panel bar chart highlighting character attribution across representative attacks.
    """
    fig, axes = plt.subplots(len(results), 1, figsize=(12, 2.5 * len(results)), sharex=False)
    if len(results) == 1:
        axes = [axes]
        
    for ax, (label, text, saliency, pred_class, conf) in zip(axes, results):
        chars = [c if c != " " else "␣" for c in text[:len(saliency)]]
        x_indices = range(len(chars))
        
        # Color mapping: Red for high saliency, Blue for low
        colors = plt.cm.YlOrRd(saliency)
        ax.bar(x_indices, saliency, color=colors, edgecolor="black", linewidth=0.5)
        
        ax.set_xticks(x_indices)
        ax.set_xticklabels(chars, fontsize=8, fontfamily="monospace", rotation=90)
        ax.set_ylabel("Saliency", fontweight="bold", fontsize=9)
        ax.set_title(f"[{label}] Pred: {pred_class.upper()} ({conf*100:.1f}%) | Text: \"{text[:50]}\"", fontsize=10, fontweight="bold", loc="left")
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.set_ylim(0, 1.1)
        
    plt.suptitle("Character-Level Token Saliency & Gradient Attribution (Explainable AI)", fontsize=13, fontweight="bold", y=1.005)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved Token Saliency Figure to: {save_path}")

def generate_html_report(results, html_path):
    """
    Generates an interactive HTML document with color-highlighted payloads.
    """
    html_content = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>KMUTNB Web Payload Explainable AI (XAI) Report</title>
<style>
body { font-family: 'Segoe UI', Arial, sans-serif; background: #0f172a; color: #f8fafc; padding: 30px; }
h1 { color: #38bdf8; border-bottom: 2px solid #38bdf8; padding-bottom: 10px; }
.card { background: #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
.badge { display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 12px; }
.badge-xss { background: #ef4444; color: white; }
.badge-sqli { background: #f59e0b; color: white; }
.badge-pathtrav { background: #8b5cf6; color: white; }
.badge-benign { background: #10b981; color: white; }
.payload-box { background: #090d16; padding: 15px; border-radius: 6px; font-family: 'Courier New', monospace; font-size: 16px; margin-top: 10px; line-height: 1.8; word-break: break-all; }
.char-span { padding: 2px 1px; border-radius: 2px; }
</style>
</head>
<body>
<h1>🛡️ Web Payload AI Model Explainability & Token Saliency Report</h1>
<p>This report highlights the exact character-level tokens that triggered the Transformer detection model using input gradient attribution.</p>
"""
    for label, text, saliency, pred_class, conf in results:
        badge_cls = f"badge-{pred_class.lower()}"
        html_content += f"""
<div class="card">
    <div>
        <span class="badge {badge_cls}">{label.upper()}</span>
        <strong>Predicted:</strong> {pred_class.upper()} (Confidence: {conf*100:.2f}%)
    </div>
    <div class="payload-box">
"""
        for char, sal in zip(text, saliency):
            # Compute alpha background from saliency
            alpha = max(0.1, sal)
            r = int(255)
            g = int(255 * (1 - sal * 0.8))
            b = int(255 * (1 - sal * 0.8))
            bg_color = f"rgba({r}, {g}, {b}, {sal*0.9:.2f})" if sal > 0.3 else "transparent"
            fg_color = "#ffffff" if sal > 0.3 else "#94a3b8"
            char_display = html.escape(char) if char != " " else "&nbsp;"
            html_content += f'<span class="char-span" style="background-color: {bg_color}; color: {fg_color};" title="Saliency: {sal:.3f}">{char_display}</span>'
            
        html_content += """
    </div>
</div>
"""
    html_content += """
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info(f"Saved Interactive HTML XAI Report to: {html_path}")

def run_saliency_analysis():
    logger.info("=== STARTING STAGE 5.2: TOKEN ATTRIBUTION & GRADIENT SALIENCY ANALYSIS ===")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using Computing Device: [{device}]")
    
    ckpt = torch.load(MODEL_PATH, map_location=device)
    model = TransformerEncoderNet(num_classes=4).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    
    analysis_results = []
    for label, text in PAYLOADS_FOR_SALIENCY:
        saliency, pred_idx, conf = compute_input_saliency(model, text, device)
        pred_class = INV_LABEL_MAP[pred_idx]
        logger.info(f"Payload [{label}] -> Predicted: {pred_class} (Conf: {conf*100:.2f}%)")
        analysis_results.append((label, text, saliency, pred_class, conf))
        
    fig_path = os.path.join(FIGURES_DIR, "token_saliency_highlighted.png")
    generate_saliency_figure(analysis_results, fig_path)
    
    html_path = os.path.join(REPORTS_DIR, "token_attribution_report.html")
    generate_html_report(analysis_results, html_path)
    
    logger.info("STAGE 5.2 COMPLETE: Token saliency figures and interactive HTML report generated.")

if __name__ == "__main__":
    run_saliency_analysis()
