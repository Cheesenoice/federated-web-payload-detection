import os
import json
import subprocess

KAGGLE_DIR = r"C:\Users\huynh\Desktop\fedwebpayload\src\stage_04_federated_learning\kaggle_train"
PYTHON_BIN = r"C:\Users\huynh\Desktop\fedwebpayload\.venv\Scripts\python.exe"

os.environ["KAGGLE_API_TOKEN"] = "KGAT_24063d4c45fa34447ab9298e00c4239f"

kernels = [
    {
        "folder": "track1_kernel",
        "slug": "stage-04-track1-centralized-fedavg",
        "ipynb": "stage_04_track1_centralized_fedavg.ipynb"
    },
    {
        "folder": "track2_kernel",
        "slug": "stage-04-track2-fedprox",
        "ipynb": "stage_04_track2_fedprox.ipynb"
    },
    {
        "folder": "track3_kernel",
        "slug": "stage-04-track3-fedavgm",
        "ipynb": "stage_04_track3_fedavgm.ipynb"
    },
    {
        "folder": "track4_kernel",
        "slug": "stage-04-track4-dafl-ensemble",
        "ipynb": "stage_04_track4_dafl_ensemble.ipynb"
    }
]

for k in kernels:
    k_dir = os.path.join(KAGGLE_DIR, k["folder"])
    os.makedirs(k_dir, exist_ok=True)
    
    # Copy ipynb
    src_ipynb = os.path.join(KAGGLE_DIR, k["ipynb"])
    dst_ipynb = os.path.join(k_dir, k["ipynb"])
    with open(src_ipynb, "r", encoding="utf-8") as f:
        content = f.read()
    with open(dst_ipynb, "w", encoding="utf-8") as f:
        f.write(content)
        
    # Write metadata
    meta = {
        "id": f"trihuynhviprovcl/{k['slug']}",
        "title": k["slug"],
        "code_file": k["ipynb"],
        "language": "python",
        "kernel_type": "notebook",
        "is_private": "false",
        "enable_gpu": "false",
        "enable_tpu": "false",
        "enable_internet": "true",
        "dataset_sources": [
            "trihuynhviprovcl/kmutnb-webpayload-full-data"
        ],
        "kernel_sources": []
    }
    with open(os.path.join(k_dir, "kernel-metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        
    print(f"Pushing kernel {k['slug']} to Kaggle...")
    res = subprocess.run([PYTHON_BIN, "-m", "kaggle", "kernels", "push", "-p", k_dir], capture_output=True, text=True)
    print(res.stdout.strip())
    if res.stderr:
        print("ERR:", res.stderr.strip())

print("\nALL 4 PARALLEL KERNELS DEPLOYED TO KAGGLE!")
