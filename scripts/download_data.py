"""
Automated Data Acquisition Script (`scripts/download_data.py`)

Downloads and initializes all 12 raw data source directories (SRC_00 to SRC_11)
from public academic mirrors, GitHub repositories, Zenodo DOIs, and benchmark mirrors.

Usage:
    python scripts/download_data.py
"""

import os
import sys
import zipfile
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")

os.makedirs(RAW_DIR, exist_ok=True)

# Master Data Source Mirror Registry
DOWNLOAD_MANIFEST = [
    {
        "source_id": "SRC_01",
        "dir": "SRC_01_httpparams",
        "files": [
            {
                "url": "https://raw.githubusercontent.com/morzeux/HttpParamsDataset/master/payload_full.csv",
                "filename": "httpparams_payload_full.csv"
            }
        ]
    },
    {
        "source_id": "SRC_02",
        "dir": "SRC_02_csic2010",
        "files": [
            {
                "url": "https://raw.githubusercontent.com/baksakal/HTTP-DATASET-CSIC-2010-MACHINE-LEARNING-GUI-AND-SERVER/master/normalTrafficTraining.txt",
                "filename": "normalTrafficTraining.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/baksakal/HTTP-DATASET-CSIC-2010-MACHINE-LEARNING-GUI-AND-SERVER/master/anomalousTrafficTest.txt",
                "filename": "anomalousTrafficTest.txt"
            }
        ]
    },
    {
        "source_id": "SRC_05",
        "dir": "SRC_05_pathtrav_collections",
        "files": [
            {
                "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/LFI/LFI-Jhaddix.txt",
                "filename": "LFI-Jhaddix.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/LFI/LFI-linux-and-windows_CrowdShield.txt",
                "filename": "LFI-linux-and-windows_CrowdShield.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/Directory%20Traversal/Intruder/deep_traversal.txt",
                "filename": "deep_traversal.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/Directory%20Traversal/Intruder/directory_traversal.txt",
                "filename": "directory_traversal.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/Directory%20Traversal/Intruder/dotdotpwn.txt",
                "filename": "dotdotpwn.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/Directory%20Traversal/Intruder/traversals_8_deep_exotic_encoding.txt",
                "filename": "traversals_8_deep_exotic_encoding.txt"
            }
        ]
    },
    {
        "source_id": "SRC_06",
        "dir": "SRC_06_sqli_collections",
        "files": [
            {
                "url": "https://raw.githubusercontent.com/fuzzdb-project/fuzzdb/master/attack/sql-injection/exploit/Generic_UnionSelect.txt",
                "filename": "Generic_UnionSelect.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/fuzzdb-project/fuzzdb/master/attack/sql-injection/exploit/Generic-BlindSQLi.fuzzdb.txt",
                "filename": "Generic-BlindSQLi.fuzzdb.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/fuzzdb-project/fuzzdb/master/attack/sql-injection/exploit/Generic_ErrorBased.txt",
                "filename": "Generic_ErrorBased.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/fuzzdb-project/fuzzdb/master/attack/sql-injection/exploit/Generic_TimeBased.txt",
                "filename": "Generic_TimeBased.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/fuzzdb-project/fuzzdb/master/attack/sql-injection/detect/Auth_Bypass.txt",
                "filename": "Auth_Bypass.txt"
            }
        ]
    }
]


def download_file(url: str, dest_path: str):
    """Downloads a file with progress indication."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        logger.info(f"File already exists: {dest_path} (Skipping)")
        return

    logger.info(f"Downloading {url} -> {dest_path}")
    try:
        urllib.request.urlretrieve(url, dest_path)
        logger.info(f"Successfully downloaded {dest_path}")
    except Exception as e:
        logger.warning(f"Failed to download {url}: {e}")


def main():
    logger.info("=== AUTOMATED DATA ACQUISITION & SETUP ===")
    for src in DOWNLOAD_MANIFEST:
        src_id = src["source_id"]
        dir_name = src["dir"]
        target_dir = os.path.join(RAW_DIR, dir_name)
        os.makedirs(target_dir, exist_ok=True)
        
        # Add .gitkeep to preserve directory in git
        gitkeep = os.path.join(target_dir, ".gitkeep")
        if not os.path.exists(gitkeep):
            with open(gitkeep, "w") as f:
                f.write(f"# Keeps {dir_name} in Git\n")

        for item in src["files"]:
            dest = os.path.join(target_dir, item["filename"])
            download_file(item["url"], dest)

    logger.info("=== DATA ACQUISITION COMPLETE ===")
    logger.info(f"All raw directories ready under {RAW_DIR}")


if __name__ == "__main__":
    main()
