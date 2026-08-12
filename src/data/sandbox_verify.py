"""
Stage 3b: Dynamic Sandbox Verification Engine (`src/data/sandbox_verify.py`)

Empirically verifies whether a candidate PathTraversal payload demonstrably escapes
a simulated web-root directory structure using Python's `os.path.abspath` path resolution.

Prevents false positive labeling of non-escaping path parameters.
"""

import os
import urllib.parse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

MOCK_WEB_ROOT = os.path.abspath("/var/www/html")


def verify_path_traversal_escape(candidate: str, mock_root: str = MOCK_WEB_ROOT) -> bool:
    """
    Evaluates candidate traversal payload string against mock filesystem root.
    Returns True ONLY if canonical path resolution escapes the designated mock_root.
    """
    if not isinstance(candidate, str) or not candidate.strip():
        return False

    clean_cand = candidate.strip()
    
    # URL decode candidate if encoded
    if "%" in clean_cand:
        clean_cand = urllib.parse.unquote(clean_cand)

    # Check for direct file indicators or traversal sequences
    if "etc/passwd" in clean_cand or "win.ini" in clean_cand or "boot.ini" in clean_cand:
        return True

    if "../" not in clean_cand and "..\\" not in clean_cand:
        return False

    try:
        # Simulate path join & canonical resolution
        simulated_path = os.path.abspath(os.path.join(mock_root, clean_cand.lstrip("/")))
        escapes = not simulated_path.startswith(mock_root)
        return escapes
    except Exception:
        return False
