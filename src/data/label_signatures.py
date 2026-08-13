"""
Strict OWASP CRS v4 Signature Engine & Label Verification (`src/data/label_signatures.py`)

Implements gold-standard regex matching aligned with OWASP CRS v4 with 3-pass URL decoding:
  - Rule 941 (XSS): Script tags, event handlers (onerror=, onload=), javascript URIs
  - Rule 942 (SQLi): SQL keywords (UNION, SELECT, OR 1=1), comment tricks, hex encodings
  - Rule 930 (PathTrav): Directory traversal sequences (../, %2e%2e%2f, /etc/passwd)
  - Multi-match Exclusion: Payloads matching 2+ attack signatures are quarantined/dropped.
"""

import re
import urllib.parse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# OWASP CRS v4 Signature Regexes
REGEX_XSS = re.compile(
    r"(?i)(<script|%3cscript|javascript:|onerror\s*=|onload\s*=|onclick\s*=|onmouseover\s*=|eval\(|document\.cookie|<iframe|alert\(|prompt\()",
    re.IGNORECASE
)

REGEX_SQLI = re.compile(
    r"(?i)(\bUNION\b\s+(\bALL\b\s+)?\bSELECT\b|\bSELECT\b.+?\bFROM\b|\bOR\b\s+['\"\d\w]+?\s*=\s*['\"\d\w]+|\bAND\b\s+['\"\d\w]+?\s*=\s*['\"\d\w]+|;\s*DROP\b|;\s*UPDATE\b|;\s*INSERT\b|/\*.*?\*/|0x[0-9a-fA-F]+|\bBENCHMARK\(|\bSLEEP\(|%27|'\s*or\s*')",
    re.IGNORECASE
)

REGEX_PATHTRAV = re.compile(
    r"(?i)(\.\.\/|\.\.\\|%2e%2e%2f|%252e%252e%252f|%2e%2e\/|\/etc\/passwd|\/etc\/shadow|c:\\windows\\win\.ini|boot\.ini)",
    re.IGNORECASE
)

REGEX_BENIGN_NUMERIC_RANGE = re.compile(r"^\d{4,5}-\d{4,5}$")


def iterative_url_decode(text: str, passes: int = 3) -> str:
    """Iteratively URL-decodes text up to `passes` times."""
    curr = str(text)
    for _ in range(passes):
        dec = urllib.parse.unquote(curr)
        if dec == curr:
            break
        curr = dec
    return curr


def verify_payload_label(payload: str, current_label: str, source: str | None = None) -> tuple[str, int]:
    """
    Verifies payload label against OWASP CRS v4 regex engine after 3-pass URL decoding.
    Returns (verified_multiclass_label, verified_binary_label).
    Multi-matches or unverified attack labels are quarantined to 'other'.
    """
    if not isinstance(payload, str) or not payload.strip():
        return "benign", 0

    raw_text = payload.strip()
    decoded_text = iterative_url_decode(raw_text, passes=3)

    if current_label == "other":
        return "other", 1

    # D19 Scrubbing: Check for benign numeric ranges
    if REGEX_BENIGN_NUMERIC_RANGE.match(raw_text) or REGEX_BENIGN_NUMERIC_RANGE.match(decoded_text):
        return "benign", 0

    # OWASP CRS v4 Signature Matching across raw and URL-decoded strings
    has_xss = bool(REGEX_XSS.search(raw_text) or REGEX_XSS.search(decoded_text))
    has_sqli = bool(REGEX_SQLI.search(raw_text) or REGEX_SQLI.search(decoded_text))
    has_pathtrav = bool(REGEX_PATHTRAV.search(raw_text) or REGEX_PATHTRAV.search(decoded_text))

    hits = [label for label, matched in (("xss", has_xss), ("sqli", has_sqli), ("pathtrav", has_pathtrav)) if matched]

    # Exactly 1 attack signature matched -> verified attack label
    if len(hits) == 1:
        return hits[0], 1

    # 2+ attack signatures matched (ambiguous multi-match) -> Quarantine to 'other'
    if len(hits) > 1:
        return "other", 1

    # 0 signatures matched: if current label was attack, quarantine it; if benign, retain benign
    if current_label in {"xss", "sqli", "pathtrav"}:
        return "other", 1

    return "benign", 0
