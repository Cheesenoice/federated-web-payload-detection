import json, glob
for f in sorted(glob.glob(r"C:\Users\huynh\Desktop\fedwebpayload\reports\stage_02_baselines\*.json")):
    data = json.load(open(f))
    model = data["model"]
    print(f"\n--- {model} ---")
    print("Pool A Test (In-Domain) F1:")
    rt = data["pool_a_test"]["report"]
    b_in = rt.get("benign", {}).get("f1-score", 0)
    x_in = rt.get("xss", {}).get("f1-score", 0)
    s_in = rt.get("sqli", {}).get("f1-score", 0)
    p_in = rt.get("pathtrav", {}).get("f1-score", 0)
    print(f"  Benign: {b_in:.4f} | XSS: {x_in:.4f} | SQLi: {s_in:.4f} | PathTrav: {p_in:.4f}")
    
    print("CSIC 2010 (OOD) F1:")
    ro = data["ood_test"]["report"]
    b_out = ro.get("benign", {}).get("f1-score", 0)
    x_out = ro.get("xss", {}).get("f1-score", 0)
    s_out = ro.get("sqli", {}).get("f1-score", 0)
    p_out = ro.get("pathtrav", {}).get("f1-score", 0)
    print(f"  Benign: {b_out:.4f} | XSS: {x_out:.4f} | SQLi: {s_out:.4f} | PathTrav: {p_out:.4f}")
