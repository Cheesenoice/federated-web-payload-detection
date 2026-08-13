"""
Stage 3a: OWASP ModSecurity CRS v4 Regex Engine & D19 Mislabel Scrubbing (`src/data/label_signatures.py`)

Implements gold-standard regex matching aligned with OWASP CRS v4:
  - Rule 941 (XSS): Script tags, event handlers (onerror=, onload=), javascript URIs
  - Rule 942 (SQLi): SQL keywords (UNION, SELECT, OR 1=1), comment tricks, hex encodings
  - Rule 930 (PathTrav): Directory traversal sequences (../, %2e%2e%2f, /etc/passwd)
  - D19 Mislabel Scrubbing: Reverts false positive labels on benign numeric/alphanumeric strings
"""

import re
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# OWASP CRS v4 Signature Regexes
REGEX_XSS = re.compile(
    r"(?i)(<script|javascript:|onerror\s*=|onload\s*=|onclick\s*=|onmouseover\s*=|eval\(|document\.cookie|<iframe|alert\(|prompt\()",
    re.IGNORECASE
)

REGEX_SQLI = re.compile(
    r"(?i)(\bUNION\b\s+(\bALL\b\s+)?\bSELECT\b|\bSELECT\b.+?\bFROM\b|\bOR\b\s+['\"\d\w]+?\s*=\s*['\"\d\w]+|\bAND\b\s+['\"\d\w]+?\s*=\s*['\"\d\w]+|;\s*DROP\b|;\s*UPDATE\b|;\s*INSERT\b|/\*.*?\*/|0x[0-9a-fA-F]+|\bBENCHMARK\(|\bSLEEP\()",
    re.IGNORECASE
)

REGEX_PATHTRAV = re.compile(
    r"(?i)(\.\.\/|\.\.\\|%2e%2e%2f|%252e%252e%252f|\/etc\/passwd|\/etc\/shadow|c:\\windows\\win\.ini|boot\.ini)",
    re.IGNORECASE
)

# D19 (Zhang et al. 2026) Benign Numeric/Alphanumeric String Scrub Pattern
REGEX_BENIGN_NUMERIC_RANGE = re.compile(r"^\d{4,5}-\d{4,5}$")
REGEX_BENIGN_SIMPLE_PARAM = re.compile(r"^[a-zA-Z0-9_\-\.\s]{1,30}$")


TRUSTED_EXPLICIT_SOURCES = {"SRC_01", "SRC_04", "SRC_05", "SRC_06"}


def verify_payload_label(payload: str, current_label: str, source: str | None = None) -> tuple[str, int]:
    """
    Verifies payload label against OWASP CRS v4 regex engine and D19 mislabel scrubbing.
    Returns (verified_multiclass_label, verified_binary_label).
    """
    if not isinstance(payload, str) or not payload.strip():
        return "benign", 0

    text = payload.strip()

    # ``other`` is an intentional quarantine class (protocol violations,
    # PHP-injection rules, command injection, feature-only records).  Never
    # silently turn it into benign merely because no payload regex matches.
    if current_label == "other":
        return "other", 1

    # Explicit dataset labels are stronger supervision than generic regexes.
    # Regexes such as ``<img src`` previously converted ordinary HTML traffic
    # into XSS, so trusted labels are retained after only the D19 scrub.
    if source in TRUSTED_EXPLICIT_SOURCES and current_label in {"benign", "xss", "sqli", "pathtrav"}:
        text = str(payload).strip()
        if REGEX_BENIGN_NUMERIC_RANGE.match(text):
            return "benign", 0
        return current_label, int(current_label != "benign")

    # D19 Scrubbing: Check for benign numeric ranges or simple safe parameter strings
    if REGEX_BENIGN_NUMERIC_RANGE.match(text) or (REGEX_BENIGN_SIMPLE_PARAM.match(text) and not REGEX_XSS.search(text) and not REGEX_SQLI.search(text) and not REGEX_PATHTRAV.search(text)):
        return "benign", 0

    # OWASP CRS v4 Signature Matching
    has_xss = bool(REGEX_XSS.search(text))
    has_sqli = bool(REGEX_SQLI.search(text))
    has_pathtrav = bool(REGEX_PATHTRAV.search(text))

    hits = [label for label, matched in (("xss", has_xss), ("sqli", has_sqli), ("pathtrav", has_pathtrav)) if matched]
    if len(hits) == 1:
        return hits[0], 1
    if len(hits) > 1 and current_label in hits:
        return current_label, 1
    if len(hits) > 1:
        return "other", 1

    # For inferred sources, an unverified attack hint is not a gold label.
    # Quarantine it instead of manufacturing a benign example.
    if current_label in {"xss", "sqli", "pathtrav"}:
        return "other", 1

    return "benign", 0
