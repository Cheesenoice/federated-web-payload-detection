import os
import glob
import pandas as pd
import torch

data_dir = "C:/Users/huynh/Desktop/fedwebpayload/src/stage_04_federated_learning/kaggle_train/fedwebpayload_full_data"

print("="*75)
print("BANG KIEM TRA 100% DU LIEU TRONG THU MUC KAGGLE DATASET")
print("="*75)

train_files = sorted(glob.glob(f"{data_dir}/clients/*_train.parquet"))
val_files = sorted(glob.glob(f"{data_dir}/clients/*_val.parquet"))
test_files = sorted(glob.glob(f"{data_dir}/clients/*_test.parquet"))

total_train = 0
total_val = 0
total_test = 0

for f in train_files:
    n = len(pd.read_parquet(f))
    total_train += n
    cid = os.path.basename(f).replace("_train.parquet", "").upper()
    print(f"  * {cid:<10} | Train: {n:>9,} samples")

for f in val_files:
    total_val += len(pd.read_parquet(f))

for f in test_files:
    total_test += len(pd.read_parquet(f))

print("-" * 75)
print(f">> TONG SO MAU TRAIN 6 CLIENT (FULL) : {total_train:>10,} samples")
print(f">> TONG SO MAU VAL   6 CLIENT (FULL) : {total_val:>10,} samples")
print(f">> TONG SO MAU TEST  6 CLIENT (FULL) : {total_test:>10,} samples")

b_df = pd.read_parquet(f"{data_dir}/pool_b_global_test.parquet")
ood_df = pd.read_parquet(f"{data_dir}/ood_csic2010.parquet")
print("-" * 75)
print(f">> TAP GLOBAL TEST B TOAN CAU (FULL) : {len(b_df):>10,} samples")
print(f">> TAP OOD CSIC 2010 NGOAI MIEN (FULL): {len(ood_df):>10,} samples")

w_base = torch.load(f"{data_dir}/W_base.pt", map_location="cpu")
print("-" * 75)
print(f">> FILE MO NEO W_BASE.PT             : HOP LE (Model: {w_base.get('model_type', 'transformer').upper()})")
print("=" * 75)
