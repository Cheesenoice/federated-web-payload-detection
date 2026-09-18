# 🚀 HƯỚNG DẪN CHẠY STAGE 4 FULL DATA (1.32M MẪU) TRÊN KAGGLE GPU

Thư mục này chứa toàn bộ dữ liệu và file Notebook đã được tối ưu hóa đặc biệt để chạy **Stage 4 Federated Learning trên toàn bộ 1.32 triệu mẫu dữ liệu thật** bằng GPU miễn phí của Kaggle (**NVIDIA Tesla T4 $\times 2$** hoặc **Tesla P100**).

---

## 📂 1. CẤU TRÚC THƯ MỤC NÀY
```
kaggle_train/
├── fedwebpayload_full_data/                 # THƯ MỤC DỮ LIỆU ĐẦY ĐỦ ĐỂ UPLOAD LÊN KAGGLE
│   ├── clients/
│   │   ├── client_1_train.parquet, client_1_val.parquet, client_1_test.parquet
│   │   ├── client_2_train.parquet, client_2_val.parquet, client_2_test.parquet
│   │   ├── client_3_train.parquet, client_3_val.parquet, client_3_test.parquet
│   │   ├── client_4_train.parquet, client_4_val.parquet, client_4_test.parquet
│   │   ├── client_5_train.parquet, client_5_val.parquet, client_5_test.parquet
│   │   └── client_6_train.parquet, client_6_val.parquet, client_6_test.parquet
│   ├── pool_b_global_test.parquet           # 354,808 mẫu test toàn cầu
│   ├── ood_csic2010.parquet                 # 122,130 mẫu kiểm thử ngoại miền OOD CSIC 2010
│   └── W_base.pt                            # Trọng số mỏ neo Transformer (~630 KB)
│
├── stage_04_full_federated_benchmark.ipynb  # FILE NOTEBOOK TỰ CHỨA ĐỂ IMPORT VÀO KAGGLE
└── README_KAGGLE.md                         # Hướng dẫn này
```

---

## 🛠️ 2. CÁC BƯỚC THỰC HIỆN TRÊN KAGGLE (CHỈ MẤT 3 PHÚT THAO TÁC)

### BƯỚC 1: NÉN DỮ LIỆU VÀ TẢI LÊN KAGGLE DATASET
1. Nén thư mục `fedwebpayload_full_data` thành file `.zip` (hoặc nén riêng thư mục `clients/` và các file `.parquet`, `.pt`).
2. Mở trình duyệt vào [Kaggle.com](https://www.kaggle.com/) $\rightarrow$ Chọn mục **Datasets** $\rightarrow$ Bấm nút **"New Dataset"** (+).
3. Đặt tiêu đề (Title): `kmutnb-webpayload-full-data`.
4. Kéo thả file `.zip` vừa nén vào khung upload $\rightarrow$ Bấm nút **"Create"** ở góc dưới.
5. Sau khi upload xong, đường dẫn dữ liệu trên Kaggle sẽ tự động là:
   `/kaggle/input/kmutnb-webpayload-full-data/`

---

### BƯỚC 2: IMPORT NOTEBOOK VÀO KAGGLE
1. Trên Kaggle, vào mục **Code** $\rightarrow$ Bấm nút **"New Notebook"** (+).
2. Trên thanh menu của Notebook, chọn **File** $\rightarrow$ **Import Notebook**.
3. Chọn file `stage_04_full_federated_benchmark.ipynb` từ máy của bạn để tải lên.

---

### BƯỚC 3: GẮN DATASET & BẬT GPU
1. Ở bảng điều khiển bên phải (Notebook Settings):
   * **Accelerator:** Chọn **GPU T4 x2** (hoặc **GPU P100**).
   * **Internet:** Bật **ON** (để nếu cần tải thêm thư viện).
2. Bấm vào nút **"+ Add Input"** (hoặc "Add Data" ở góc trên bên phải):
   * Tìm dataset `kmutnb-webpayload-full-data` bạn vừa tạo ở Bước 1 và bấm dấu **(+) Add**.

---

### BƯỚC 4: CHẠY HUẤN LUYỆN
* **Cách 1 (Chạy trực tiếp xem tiến độ):** Chọn **Run** $\rightarrow$ **Run All** (hoặc bấm `Ctrl + F10`).
* **Cách 2 (Chạy ngầm tắt máy đi ngủ):** Bấm nút **"Save Version"** ở góc trên bên phải $\rightarrow$ Chọn **"Save & Run All (Commit)"** $\rightarrow$ Bấm **Save**.
  *(Kaggle sẽ tự động chạy toàn bộ 10 rounds của 5 thuật toán FL trong nền. Bạn có thể tắt máy tính, sau 1–2 tiếng quay lại tải toàn bộ Bảng kết quả, Checkpoints và Biểu đồ về).*

---

## 📊 KẾT QUẢ ĐẦU RA SẼ NẰM TẠI `/kaggle/working/`:
* `models/W_centralized.pt`, `W_fedavg.pt`, `W_fedprox.pt`, `W_fedavgm.pt`, `W_dafl.pt`, `W_ensemble.pt`
* `models/round_checkpoints/*.pt` (Lưu chi tiết từng round)
* `reports/federated_algorithms_master_benchmark.csv` (Bảng 4 Master Benchmark)
* `reports/figures/fig1_convergence_comparison.png` (Đồ thị hội tụ)
* `reports/figures/fig2_ood_generalization_gap.png` (Đồ thị OOD)
