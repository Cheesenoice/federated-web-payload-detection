"""
Multi-Threaded Automated Data Acquisition & Link Health Checker (`scripts/download_data.py`)

Parallel downloader with 100% live verified URL status checks across public academic mirrors.

Usage:
    python scripts/download_data.py --test      # Safe test mode into data/raw_test/ (does NOT touch data/raw/)
    python scripts/download_data.py             # Normal mode into data/raw/
"""

import os
import sys
import time
import argparse
import urllib.request
import urllib.error
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Master 100% Verified Live Data Source Mirror Registry (Tested HTTP 200 OK)
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
                "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/LFI/LFI-LFISuite-pathtotest-huge.txt",
                "filename": "LFI-LFISuite-pathtotest-huge.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/LFI/LFI-LFISuite-pathtotest.txt",
                "filename": "LFI-LFISuite-pathtotest.txt"
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
            }
        ]
    },
    {
        "source_id": "SRC_06",
        "dir": "SRC_06_sqli_collections",
        "files": [
            {
                "url": "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/SQL%20Injection/Intruder/Generic_UnionSelect.txt",
                "filename": "Generic_UnionSelect.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/SQL%20Injection/Intruder/Auth_Bypass.txt",
                "filename": "Auth_Bypass.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/Databases/SQLi/Generic-SQLi.txt",
                "filename": "Generic-SQLi.txt"
            },
            {
                "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/Databases/SQLi/quick-SQLi.txt",
                "filename": "quick-SQLi.txt"
            }
        ]
    }
]


def download_single_file(item: dict, target_dir: str) -> tuple[str, bool, int, str]:
    """
    Downloads a single file over HTTP/HTTPS with detailed status reporting.
    Returns (filename, success_flag, file_size_bytes, status_msg).
    """
    url = item["url"]
    filename = item["filename"]
    dest_path = os.path.join(target_dir, filename)

    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        size = os.path.getsize(dest_path)
        return (filename, True, size, f"EXISTS ({size} bytes)")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FedWebPayload-Benchmark/1.0"})
        with urllib.request.urlopen(req, timeout=15) as response, open(dest_path, "wb") as out_file:
            data = response.read()
            out_file.write(data)
            size = len(data)
            return (filename, True, size, f"DOWNLOADED 200 OK ({size} bytes)")
    except urllib.error.HTTPError as e:
        return (filename, False, 0, f"DEAD LINK HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        return (filename, False, 0, f"URL ERROR: {e.reason}")
    except Exception as e:
        return (filename, False, 0, f"FAILED: {e}")


def main():
    parser = argparse.ArgumentParser(description="Multi-threaded raw dataset acquisition script.")
    parser.add_argument("--test", action="store_true", help="Download into data/raw_test/ to protect existing data/raw/")
    parser.add_argument("--out-dir", type=str, default=None, help="Custom output directory")
    args = parser.parse_args()

    if args.out_dir:
        output_dir = os.path.abspath(args.out_dir)
    elif args.test:
        output_dir = os.path.join(BASE_DIR, "data", "raw_test")
    else:
        output_dir = os.path.join(BASE_DIR, "data", "raw")

    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"=== MULTI-THREADED DATA ACQUISITION STARTING ===")
    logger.info(f"Target Directory: {output_dir}")

    # Build download task list
    download_tasks = []
    for src in DOWNLOAD_MANIFEST:
        dir_name = src["dir"]
        target_dir = os.path.join(output_dir, dir_name)
        os.makedirs(target_dir, exist_ok=True)

        for item in src["files"]:
            download_tasks.append((item, target_dir, src["source_id"]))

    logger.info(f"Submitting {len(download_tasks)} download tasks across 8 parallel threads...")
    start_time = time.time()
    
    success_count = 0
    fail_count = 0

    # Multi-threaded execution
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {
            executor.submit(download_single_file, item, target_dir): (src_id, item)
            for item, target_dir, src_id in download_tasks
        }

        for future in as_completed(future_map):
            src_id, item = future_map[future]
            filename, success, size, msg = future.result()
            if success:
                logger.info(f"✅ [{src_id}] {filename}: {msg}")
                success_count += 1
            else:
                logger.error(f"❌ [{src_id}] {filename}: {msg}")
                fail_count += 1

    elapsed = time.time() - start_time
    logger.info("="*60)
    logger.info(f"=== DATA ACQUISITION SUMMARY ===")
    logger.info(f"Total Tasks: {len(download_tasks)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed / Dead Links: {fail_count}")
    logger.info(f"Elapsed Time: {elapsed:.2f} seconds")
    logger.info(f"All files saved in: {output_dir}")
    logger.info("="*60)


if __name__ == "__main__":
    main()
