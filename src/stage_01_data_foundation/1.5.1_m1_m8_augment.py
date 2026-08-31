"""
Deterministic Semantic Augmentation Engine (M1–M8)
Path: `src/stage_01_data_foundation/1.5.1_m1_m8_augment.py`

Applies 8 deterministic mutation rules (M1–M8) to expand minority attack classes
(PathTraversal & SQL Injection) for Pool A Base Model pre-training:
  - M1: Case Toggling
  - M2: Single URL Encoding
  - M3: Double URL Encoding
  - M4: Space-to-Comment Injection
  - M5: Logical Operator Swap
  - M6: Null-Byte Injection
  - M7: Path Depth Extension
  - M8: Path Separator Obfuscation

CRITICAL SCIENTIFIC CONSTRAINT:
Every augmented variant inherits its parent seed's `exact_cluster_id`.
"""

import re
import urllib.parse

def apply_sqli_mutations(payload: str) -> list[str]:
    """Generates deterministic semantic variants for SQLi seeds."""
    variants = [payload]
    
    # Rule M1: Case Toggling
    toggled = "".join(c.upper() if idx % 2 == 0 else c.lower() for idx, c in enumerate(payload))
    variants.append(toggled)

    # Rule M4: Space-to-Comment Injection
    if " " in payload:
        variants.append(re.sub(r"\s+", "/**/", payload))

    # Rule M5: Logical Operator Swap
    if " OR " in payload.upper():
        variants.append(re.sub(r"\bOR\b", "||", payload, flags=re.IGNORECASE))
    if " AND " in payload.upper():
        variants.append(re.sub(r"\bAND\b", "&&", payload, flags=re.IGNORECASE))

    # Rule M2: Single URL Encoding
    if "'" in payload or "=" in payload or " " in payload:
        variants.append(urllib.parse.quote(payload, safe=""))

    return list(dict.fromkeys(variants)) # Deduplicate while preserving order


def apply_pathtrav_mutations(payload: str) -> list[str]:
    """Generates deterministic semantic variants for PathTrav seeds."""
    variants = [payload]

    # Rule M2: Single URL Encoding
    if "../" in payload or "..\\" in payload:
        v_url = payload.replace("../", "%2e%2e%2f").replace("..\\", "%2e%2e%5c")
        variants.append(v_url)
        # Rule M3: Double URL Encoding
        variants.append(v_url.replace("%2e", "%252e").replace("%2f", "%252f"))

    # Rule M7: Path Depth Extension
    if "../" in payload:
        variants.append(payload.replace("../", "../../"))
        variants.append(payload.replace("../", "../../../"))

    # Rule M8: Path Separator Obfuscation
    if "../" in payload:
        variants.append(payload.replace("../", "....//"))
        variants.append(payload.replace("../", "..\\/"))

    # Rule M6: Null Byte Injection
    if "passwd" in payload or "win.ini" in payload or "boot.ini" in payload:
        variants.append(payload + "%00")

    return list(dict.fromkeys(variants)) # Deduplicate while preserving order


def apply_xss_mutations(payload: str) -> list[str]:
    """Generates deterministic semantic variants for XSS seeds."""
    variants = [payload]
    
    # Rule M1: Case Toggling
    toggled = "".join(c.upper() if idx % 2 == 0 else c.lower() for idx, c in enumerate(payload))
    variants.append(toggled)
    
    # Rule M2: Single URL Encoding
    if "<" in payload or ">" in payload:
        variants.append(urllib.parse.quote(payload, safe=""))
        
    return list(dict.fromkeys(variants))
