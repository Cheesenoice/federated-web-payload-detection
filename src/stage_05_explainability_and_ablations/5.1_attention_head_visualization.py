import os
import sys
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

# Canonical Representative Payloads for Qualitative Inspection
SAMPLE_PAYLOADS = [
    ("XSS", "<script>alert(document.cookie)</script>", "attention_heatmaps_xss.png"),
    ("XSS_Obfuscated", "<img src=x onerror=prompt('XSS_ATTACK')>", "attention_heatmaps_xss_img.png"),
    ("SQLi", "' UNION SELECT 1, column_name, 3 FROM information_schema.columns--", "attention_heatmaps_sqli.png"),
    ("SQLi_AuthBypass", "admin' OR '1'='1' #", "attention_heatmaps_sqli_auth.png"),
    ("PathTraversal", "../../../../etc/passwd%00", "attention_heatmaps_pathtrav.png"),
    ("PathTrav_Windows", "..\\..\\..\\windows\\system32\\cmd.exe", "attention_heatmaps_pathtrav_win.png"),
    ("Benign_Search", "/products/search?category=security&order=asc&page=1", "attention_heatmaps_benign.png")
]

class ExplainableTransformer(nn.Module):
    """
    Transformer model wrapping custom forward logic to extract exact multi-head attention weights.
    """
    def __init__(self, base_transformer):
        super(ExplainableTransformer, self).__init__()
        self.token_embedding = base_transformer.token_embedding
        self.pos_embedding = base_transformer.pos_embedding
        self.transformer_encoder = base_transformer.transformer_encoder
        self.ln = base_transformer.ln
        self.dropout = base_transformer.dropout
        self.fc = base_transformer.fc

    def forward_with_attention(self, x):
        # x: [1, seq_len]
        seq_len = x.size(1)
        padding_mask = (x == 0)
        
        emb = self.token_embedding(x) + self.pos_embedding[:, :seq_len, :]
        
        # We manually pass through transformer layers to capture attention maps
        h = emb
        attn_maps = []
        for layer in self.transformer_encoder.layers:
            # Self-attention with output_weights
            # PyTorch MultiheadAttention
            attn_out, attn_weights = layer.self_attn(
                h, h, h,
                key_padding_mask=padding_mask,
                need_weights=True,
                average_attn_weights=False # returns [batch, num_heads, seq_len, seq_len]
            )
            h = layer.norm1(h + layer.dropout1(attn_out))
            ff_out = layer.linear2(layer.dropout(layer.activation(layer.linear1(h))))
            h = layer.norm2(h + layer.dropout2(ff_out))
            attn_maps.append(attn_weights.detach().cpu())
            
        mask = (~padding_mask).unsqueeze(-1).float()
        pooled = torch.sum(h * mask, dim=1) / torch.clamp(mask.sum(dim=1), min=1.0)
        pooled = self.ln(pooled)
        logits = self.fc(pooled)
        return logits, attn_maps

def plot_attention_map(payload_text, tokens, attn_matrix, attack_label, save_path):
    """
    Plots a high-resolution 2D Attention Heatmap over the active characters of the payload.
    """
    # Crop to the active length of the payload (max 40 chars for clean readability)
    active_len = min(len(payload_text), 40)
    chars = [c if c != " " else "␣" for c in payload_text[:active_len]]
    attn_crop = attn_matrix[:active_len, :active_len]
    
    # Normalize for visual clarity
    attn_crop = attn_crop / (attn_crop.max() + 1e-8)
    
    plt.figure(figsize=(9, 7))
    plt.imshow(attn_crop, cmap="YlOrRd", interpolation="nearest")
    plt.title(f"Multi-Head Self-Attention Map | Class: {attack_label}\nPayload: \"{payload_text[:45]}...\"", fontsize=11, fontweight="bold")
    plt.colorbar(label="Normalized Attention Weight")
    
    plt.xticks(range(active_len), chars, rotation=90, fontsize=9, fontfamily="monospace")
    plt.yticks(range(active_len), chars, fontsize=9, fontfamily="monospace")
    
    plt.xlabel("Key Token Position", fontweight="bold")
    plt.ylabel("Query Token Position", fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved Attention Heatmap to: {save_path}")

def run_attention_visualization():
    logger.info("=== STARTING STAGE 5.1: MULTI-HEAD SELF-ATTENTION VISUALIZATION ===")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using Computing Device: [{device}]")
    
    # 1. Load Pre-trained / Federated Model Checkpoint
    logger.info(f"Loading Model Checkpoint from: {MODEL_PATH}")
    ckpt = torch.load(MODEL_PATH, map_location=device)
    base_model = TransformerEncoderNet(num_classes=4).to(device)
    base_model.load_state_dict(ckpt["model_state_dict"])
    base_model.eval()
    
    explainer = ExplainableTransformer(base_model).to(device)
    explainer.eval()
    
    # 2. Iterate through Sample Payloads and Generate Attention Maps
    for label, payload, filename in SAMPLE_PAYLOADS:
        tokens = encode_payload(payload, max_len=256)
        x_tensor = torch.tensor(tokens, dtype=torch.long).unsqueeze(0).to(device)
        
        with torch.no_grad():
            logits, attn_layers = explainer.forward_with_attention(x_tensor)
            pred_idx = torch.argmax(logits, dim=1).item()
            pred_class = INV_LABEL_MAP[pred_idx]
            conf = F.softmax(logits, dim=1)[0, pred_idx].item()
            
        logger.info(f"Payload [{label}] -> Predicted: [{pred_class.upper()}] (Confidence: {conf*100:.2f}%)")
        
        # Take the attention map from the final Transformer layer (Layer 3), averaged across heads
        # attn_layers[-1] shape: [1, num_heads, seq_len, seq_len]
        final_layer_attn = attn_layers[-1][0].mean(dim=0).numpy()
        
        save_path = os.path.join(FIGURES_DIR, filename)
        plot_attention_map(payload, tokens, final_layer_attn, f"{label} (Pred: {pred_class}, {conf*100:.1f}%)", save_path)
        
    logger.info("STAGE 5.1 COMPLETE: All attention heatmaps generated successfully.")

if __name__ == "__main__":
    run_attention_visualization()
