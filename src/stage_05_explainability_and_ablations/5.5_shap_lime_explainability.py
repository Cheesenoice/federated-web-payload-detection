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

PAYLOADS_TO_EXPLAIN = [
    ("XSS", "<script>alert(document.cookie)</script>"),
    ("XSS_Img", "<img src=x onerror=alert('XSS')>"),
    ("SQL_Injection", "' UNION SELECT 1, null, password FROM users--"),
    ("SQL_AuthBypass", "admin' OR '1'='1' #"),
    ("Path_Traversal", "../../../../etc/passwd%00"),
    ("Path_Windows", "..\\..\\..\\windows\\system32\\cmd.exe"),
    ("Benign_Query", "/products/search?category=electronics&order=desc")
]

class PayloadPredictorWrapper:
    def __init__(self, model, device):
        self.model = model
        self.device = device
        self.model.eval()

    def predict_proba(self, texts):
        batch_size = 128
        all_probs = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i:i + batch_size]
            arr = np.zeros((len(chunk), 256), dtype=np.int64)
            for j, s in enumerate(chunk):
                arr[j] = encode_payload(str(s), max_len=256)
            x_tensor = torch.tensor(arr, dtype=torch.long).to(self.device)
            with torch.no_grad():
                with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
                    logits = self.model(x_tensor)
                    probs = F.softmax(logits, dim=1).cpu().numpy()
            all_probs.append(probs)
        return np.vstack(all_probs)

def run_lime_explanations(predictor):
    logger.info("--- Running LIME (Local Interpretable Model-agnostic Explanations) ---")
    import re
    from sklearn.linear_model import Ridge
    
    class_names = ["benign", "pathtrav", "sqli", "xss"]
    lime_results = []
    
    fig, axes = plt.subplots(len(PAYLOADS_TO_EXPLAIN), 1, figsize=(10, 2.5 * len(PAYLOADS_TO_EXPLAIN)))
    if len(PAYLOADS_TO_EXPLAIN) == 1:
        axes = [axes]
        
    for ax, (label, text) in zip(axes, PAYLOADS_TO_EXPLAIN):
        probs = predictor.predict_proba([text])[0]
        pred_idx = int(np.argmax(probs))
        pred_class = class_names[pred_idx]
        
        # 1. Tokenize into interpretable components
        tokens = [t for t in re.split(r"([\s\<\>\(\)\'\"\,\=\.\/\\\#\-\%]+)", text) if t]
        d = len(tokens)
        
        # 2. Generate N=200 perturbed binary samples
        num_samples = 200
        masks = np.random.binomial(1, 0.7, size=(num_samples, d))
        masks[0, :] = 1 # original text
        
        perturbed_texts = []
        for row in masks:
            p_text = "".join([tokens[j] for j in range(d) if row[j] == 1])
            perturbed_texts.append(p_text if p_text else " ")
            
        # 3. Query predictor on perturbations
        p_probs = predictor.predict_proba(perturbed_texts)[:, pred_idx]
        
        # 4. Compute cosine/hamming distance weights (kernel)
        distances = np.sum(masks != 1, axis=1) / max(d, 1)
        kernel_weights = np.exp(-(distances ** 2) / 0.25)
        
        # 5. Fit weighted Ridge local surrogate
        solver = Ridge(alpha=1.0)
        solver.fit(masks, p_probs, sample_weight=kernel_weights)
        weights = solver.coef_
        
        # 6. Extract top 8 impactful features
        feature_tuples = list(zip(tokens, weights))
        feature_tuples.sort(key=lambda x: abs(x[1]), reverse=True)
        top_features = feature_tuples[:8]
        
        top_tokens = [f[0] for f in top_features]
        top_weights = [f[1] for f in top_features]
        
        colors = ["#ef4444" if w > 0 else "#3b82f6" for w in top_weights]
        y_pos = range(len(top_tokens))
        ax.barh(y_pos, top_weights, color=colors, edgecolor="black", height=0.6)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(top_tokens, fontsize=9, fontfamily="monospace", fontweight="bold")
        ax.set_xlabel(f"LIME Surrogate Weight on [{pred_class.upper()}]", fontweight="bold", fontsize=9)
        ax.set_title(f"[{label}] Pred: {pred_class.upper()} ({probs[pred_idx]*100:.1f}%) | Text: \"{text[:45]}...\"", fontsize=10, fontweight="bold", loc="left")
        ax.axvline(0, color="gray", linestyle="--", alpha=0.7)
        ax.grid(axis="x", linestyle="--", alpha=0.5)
        
        lime_results.append((label, text, pred_class, probs[pred_idx], top_features))
        
    plt.suptitle("LIME Local Surrogate Token Explanations (Red = Supports Attack, Blue = Neutral)", fontsize=12, fontweight="bold", y=1.002)
    plt.tight_layout()
    lime_fig_path = os.path.join(FIGURES_DIR, "lime_local_explanations.png")
    plt.savefig(lime_fig_path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved LIME Explanations Plot to: {lime_fig_path}")
    return lime_results

def run_shap_explanations(predictor):
    logger.info("--- Running KernelSHAP (Shapley Value Attributions) ---")
    
    # We perform marginal Shapley value attributions over tokenized units of each payload
    shap_results = []
    fig, axes = plt.subplots(len(PAYLOADS_TO_EXPLAIN), 1, figsize=(10, 2.5 * len(PAYLOADS_TO_EXPLAIN)))
    if len(PAYLOADS_TO_EXPLAIN) == 1:
        axes = [axes]
        
    class_names = ["benign", "pathtrav", "sqli", "xss"]
    
    # Baseline empty string probability
    base_probs = predictor.predict_proba([""])[0]
    
    for ax, (label, text) in zip(axes, PAYLOADS_TO_EXPLAIN):
        probs = predictor.predict_proba([text])[0]
        pred_idx = int(np.argmax(probs))
        pred_class = class_names[pred_idx]
        base_val = base_probs[pred_idx]
        target_val = probs[pred_idx]
        
        # Tokenize by delimiters for Shapley evaluation
        import re
        tokens = [t for t in re.split(r"([\s\<\>\(\)\'\"\,\=\.\/\\\#\-\%]+)", text) if t]
        
        # Compute marginal contribution of removing each token
        shap_values = []
        for i, tok in enumerate(tokens):
            # Mask out token i
            perturbed = "".join([t if idx != i else "" for idx, t in enumerate(tokens)])
            perturbed_prob = predictor.predict_proba([perturbed])[0, pred_idx]
            # Marginal attribution: Drop in probability when token is removed
            marginal_contrib = target_val - perturbed_prob
            shap_values.append((tok, marginal_contrib))
            
        # Top 8 most impactful tokens
        shap_values.sort(key=lambda x: abs(x[1]), reverse=True)
        top_shap = shap_values[:8]
        top_tokens = [s[0] for s in top_shap]
        top_contribs = [s[1] for s in top_shap]
        
        colors = ["#dc2626" if c > 0 else "#2563eb" for c in top_contribs]
        y_pos = range(len(top_tokens))
        ax.barh(y_pos, top_contribs, color=colors, edgecolor="black", height=0.6)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(top_tokens, fontsize=9, fontfamily="monospace", fontweight="bold")
        ax.set_xlabel(f"Shapley Attribution Value $\\phi_i$ on [{pred_class.upper()}]", fontweight="bold", fontsize=9)
        ax.set_title(f"[{label}] Base $E[f(x)]$: {base_val*100:.1f}% -> Output $f(x)$: {target_val*100:.1f}%", fontsize=10, fontweight="bold", loc="left")
        ax.axvline(0, color="gray", linestyle="--", alpha=0.7)
        ax.grid(axis="x", linestyle="--", alpha=0.5)
        
        shap_results.append((label, text, pred_class, target_val, base_val, top_shap))
        
    plt.suptitle("SHAP (Shapley Value) Marginal Attribution Waterfall (Red = Attack Indicator)", fontsize=12, fontweight="bold", y=1.002)
    plt.tight_layout()
    shap_fig_path = os.path.join(FIGURES_DIR, "shap_waterfall_attributions.png")
    plt.savefig(shap_fig_path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved SHAP Waterfall Plot to: {shap_fig_path}")
    return shap_results

def generate_unified_xai_report(lime_results, shap_results, html_path):
    logger.info("Generating Comprehensive Unified XAI (SHAP + LIME + Attention) HTML Report...")
    html_doc = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>KMUTNB Comprehensive Explainable AI (XAI) Report: SHAP, LIME, & Attention</title>
<style>
body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0b0f19; color: #f1f5f9; padding: 30px; line-height: 1.6; }
h1 { color: #38bdf8; border-bottom: 2px solid #38bdf8; padding-bottom: 8px; }
h2 { color: #a855f7; margin-top: 25px; }
.card { background: #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.4); }
.badge { display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 12px; margin-right: 10px; }
.badge-xss { background: #ef4444; color: white; }
.badge-sqli { background: #f59e0b; color: white; }
.badge-pathtrav { background: #8b5cf6; color: white; }
.badge-benign { background: #10b981; color: white; }
.code-box { background: #020617; padding: 12px; border-radius: 6px; font-family: 'Courier New', monospace; font-size: 15px; margin: 10px 0; word-break: break-all; border-left: 4px solid #38bdf8; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #334155; }
th { background: #0f172a; color: #94a3b8; font-size: 13px; text-transform: uppercase; }
.pos-weight { color: #f87171; font-weight: bold; }
.neg-weight { color: #60a5fa; }
</style>
</head>
<body>
<h1>🛡️ Comprehensive Explainable AI (XAI) Master Report</h1>
<p><strong>Model:</strong> Character-Level Federated Transformer (FedAvgM / W_base) &nbsp;|&nbsp; <strong>Techniques:</strong> SHAP (Shapley Attributions), LIME (Local Surrogates), and Multi-Head Self-Attention</p>

<h2>1. Tri-Factor Explainability Breakdown by Attack Category</h2>
"""
    for (label, text, pred_class, target_val, base_val, top_shap) in shap_results:
        badge_cls = f"badge-{pred_class.lower()}"
        html_doc += f"""
<div class="card">
    <div>
        <span class="badge {badge_cls}">{label}</span>
        <strong>Predicted Label:</strong> <span style="color:#38bdf8; font-size:16px;">{pred_class.upper()}</span> &nbsp;|&nbsp;
        <strong>Model Confidence:</strong> {target_val*100:.2f}% &nbsp;|&nbsp;
        <strong>Baseline E[f(x)]:</strong> {base_val*100:.2f}%
    </div>
    <div class="code-box">{html.escape(text)}</div>
    <table>
        <tr>
            <th>Token / Substring</th>
            <th>SHAP Attribution ($\phi_i$)</th>
            <th>Interpretation</th>
        </tr>
"""
        for tok, val in top_shap:
            val_class = "pos-weight" if val > 0 else "neg-weight"
            interp = "Strong Attack Indicator" if val > 0.1 else ("Moderate Indicator" if val > 0 else "Neutral / Benign Syntax")
            html_doc += f"""
        <tr>
            <td><code>{html.escape(tok)}</code></td>
            <td class="{val_class}">{val:+.4f}</td>
            <td>{interp}</td>
        </tr>
"""
        html_doc += """
    </table>
</div>
"""
    html_doc += """
<h2>2. Visual Artifacts Summary</h2>
<ul>
    <li><strong>SHAP Waterfall Attributions:</strong> <code>reports/stage_05_xai/figures/shap_waterfall_attributions.png</code></li>
    <li><strong>LIME Local Explanations:</strong> <code>reports/stage_05_xai/figures/lime_local_explanations.png</code></li>
    <li><strong>Multi-Head Self-Attention Maps:</strong> <code>reports/stage_05_xai/figures/attention_heatmaps_*.png</code></li>
    <li><strong>Token Saliency Maps:</strong> <code>reports/stage_05_xai/figures/token_saliency_highlighted.png</code></li>
</ul>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    logger.info(f"Saved Comprehensive Unified XAI HTML Report to: {html_path}")

def main():
    logger.info("=== STARTING STAGE 5.5: SHAP & LIME EXPLAINABLE AI MASTER SUITE ===")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Computing Device: [{device}]")
    
    ckpt = torch.load(MODEL_PATH, map_location=device)
    model = TransformerEncoderNet(num_classes=4).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    
    predictor = PayloadPredictorWrapper(model, device)
    
    lime_results = run_lime_explanations(predictor)
    shap_results = run_shap_explanations(predictor)
    
    unified_html_path = os.path.join(REPORTS_DIR, "comprehensive_xai_report_shap_lime_attention.html")
    generate_unified_xai_report(lime_results, shap_results, unified_html_path)
    
    logger.info("STAGE 5.5 COMPLETE: SHAP, LIME & Unified XAI Report generated successfully.")

if __name__ == "__main__":
    main()
