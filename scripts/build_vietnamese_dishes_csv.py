"""Build cleaned Vietnamese dishes CSV from the user-provided ViFoodRec archive.

Input archive (user-provided):
- A-New-Dataset-and-Empirical-Evaluation-for-Vietnamese-Food-Recommendation-System-main.zip
  - Data/Clean Dataset/foods.csv (4,000 rows)
  - Data/Raw Dataset/food_dataset_mnmnweb.csv (1,213 rows — recovers Cách dùng & Mách nhỏ)

Quality & honesty fixes applied:
1. Drops synthetic uniform-random columns from ViFoodRec (ratings.csv and fake
   random calories/fat/fiber/sugar/protein).
2. Fixes encoding (100% Unicode NFC) and upstream text-replacement corruption
   (e.g., 394 occurrences of 'muỗngiếng' -> 'miếng').
3. Filters out non-Vietnamese foreign dishes (pizza, sushi, spaghetti, latte, etc.).
4. Re-classifies dish categories (fixing desserts/drinks wrongly tagged 'Món mặn').
5. Extracts serving temperature (nóng / ấm / nguội / lạnh) deterministically from
   'Cách dùng', 'Cách làm', and 'Mô tả'.
6. Deduplicates strictly by normalized dish name and ingredient hash.
7. Optionally enriches real reference nutrition by matching Vietnamese ingredients
   against data/raw/nin_vietnam_nutrition_mit.json (if present).

Output:
- data/processed/vietnamese_dishes.csv
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import os
import re
import unicodedata
import zipfile
from collections import Counter
from datetime import date

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(REPO_ROOT, "data", "raw")
OUT_DIR = os.path.join(REPO_ROOT, "data", "processed")
ZIP_PATH = r"C:\Users\duyma\.gemini\antigravity\brain\301da5b8-3680-4646-9d02-8476cbdf6de6\.user_uploaded\media_1795758108836_cf361006.zip"

TODAY = date.today().isoformat()

FOREIGN_DISH_PAT = re.compile(
    r"\b("
    r"latte|cappuccino|espresso|americano|macchiato|mocha|matcha\s*latte|"
    r"cheesecake|tiramisu|brownie|cupcake|muffin|pancake|waffle|croissant|macaron|panna\s*cotta|creme\s*brulee|"
    r"pizza|spaghetti|pasta|lasagna|risotto|carbonara|bolognese|ravioli|gnocchi|"
    r"hamburger|burger|hotdog|hot\s*dog|sandwich\s*phô\s*mai|steak\s*kiểu\s*âu|beefsteak|bít\s*tết\s*kiểu\s*âu|"
    r"sushi|sashimi|ramen|udon|soba|tempura|teriyaki|takoyaki|okonomiyaki|onigiri|tonkatsu|katsudon|miso\s*soup|"
    r"kimchi|kim\s*chi|tokbokki|tteokbokki|kimbap|gimbap|bibimbap|bulgogi|jajangmyeon|mi\s*cay\s*hàn\s*quốc|gà\s*rút\s*xương\s*phô\s*mai|"
    r"tacos|burrito|nachos|quesadilla|pad\s*thai|tom\s*yum|tomyum|cà\s*ri\s*nhật|cà\s*ri\s*ấn|dimsum|dim\s*sum|"
    r"salad\s*caesar|caesar\s*salad|smoothie\s*bowl|milkshake"
    r")\b",
    re.I,
)


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFC", html.unescape(str(text)))
    s = s.replace("\ufeff", "").replace("\x00", "").replace("\xa0", " ")
    s = re.sub(r"<[^>]+>", " ", s)
    # Fix upstream ViFoodRec replace corruption (e.g. 'ml' -> 'muỗngl', 'miếng' -> 'muỗngiếng')
    s = re.sub(r"muỗng(?=[a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ])", "m", s, flags=re.I)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def normalize_title_case(name: str) -> str:
    """Fix weird mixed casing like 'SữA Chua Trân Châu TráI Cây'."""
    s = clean_text(name)
    # If there are mid-word uppercase Vietnamese letters (artifact of NFD title-casing)
    if re.search(r"[a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ][A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]", s):
        s = s.lower()
        s = s[0].upper() + s[1:] if s else s
    return s


def classify_dish(name: str, raw_type: str, ing: str, method: str) -> str:
    low = name.lower()
    if "chay" in raw_type.lower() or "chay" in low:
        return "Món chay"
    if re.search(r"\b(trà|nước ép|sinh tố|cà phê|sữa hạt|sữa chua|nước mát|nước sâm|nước mía|nước chanh|chanh muối|nước tắc|thức uống)\b", low):
        return "Đồ uống"
    if re.search(r"\b(chè|rau câu|thạch|bánh flan|kem|mứt|kẹo|tàu hũ|tào phớ|xôi chè|sương sáo|sương sâm|tráng miệng)\b", low):
        return "Chè / Tráng miệng"
    if re.search(r"\b(phở|bún|mì|miến|hủ tiếu|bánh canh|cao lầu|bánh đa cua|nui)\b", low):
        return "Phở / Bún / Mì"
    if re.search(r"\b(cơm|xôi|cháo)\b", low):
        return "Cơm / Xôi / Cháo"
    if re.search(r"\b(canh|súp|lẩu|riêu)\b", low):
        return "Canh / Súp / Lẩu"
    if re.search(r"\b(gỏi|nộm|cuốn|bò bía|nem cuốn|phở cuốn|salad)\b", low):
        return "Gỏi / Nộm / Cuốn"
    if re.search(r"\b(bánh)\b", low):
        return "Bánh truyền thống"
    if re.search(r"\b(nước mắm|nước chấm|mắm nêm|mắm tôm|muối tiêu|muối ớt|tương ớt|đồ chua|dưa góp|dưa muối|cà pháo|dưa món|sa tế)\b", low):
        return "Nước chấm / Đồ chua"
    if re.search(r"\b(kho|rim|om|khìa|hầm|tiềm|ragu|cà ri|bò kho)\b", low):
        return "Kho / Rim / Om / Hầm"
    if re.search(r"\b(nướng|hấp|luộc|chưng|quay)\b", low):
        return "Nướng / Hấp / Luộc"
    if re.search(r"\b(xào|chiên|rán|rang|lắc|áp chảo|sốt|xốt|chả|nem rán|chả giò)\b", low):
        return "Xào / Chiên / Rán"
    return "Món mặn truyền thống"


def extract_serving_temp(cach_dung: str, method: str, desc: str, loai_mon: str) -> str:
    primary = (cach_dung + " " + desc).lower()
    full = (cach_dung + " " + method + " " + desc).lower()

    has_hot = bool(re.search(r"\b(dùng nóng|ăn nóng|thưởng thức nóng|khi còn nóng|còn nóng|múc ra tô nóng|nóng hổi|ăn ngay khi nóng)\b", primary))
    has_warm = bool(re.search(r"\b(dùng ấm|ăn ấm|còn ấm|uống ấm)\b", primary))
    has_cold = bool(re.search(r"\b(dùng lạnh|ăn lạnh|uống lạnh|ướp lạnh|ngăn mát|thêm đá|đá viên|đá bào|mát lạnh|giải nhiệt)\b", primary))
    has_room = bool(re.search(r"\b(ăn nguội|dùng nguội|để nguội|nguội hẳn)\b", primary))

    if has_hot and has_cold:
        return "nóng hoặc lạnh"
    if has_cold:
        return "lạnh"
    if has_hot:
        return "nóng"
    if has_warm:
        return "ấm"
    if has_room:
        return "nguội"

    # Secondary check in full method text
    if re.search(r"\b(dùng nóng|ăn nóng|khi còn nóng|thưởng thức ngay khi nóng)\b", full):
        return "nóng"
    if re.search(r"\b(dùng lạnh|ăn lạnh|uống lạnh|thêm đá|ngăn mát tủ lạnh)\b", full):
        return "lạnh"
    if re.search(r"\b(ăn nguội|dùng nguội)\b", full):
        return "nguội"

    if loai_mon in ("Đồ uống", "Chè / Tráng miệng"):
        return "lạnh / mát (theo nhóm món)"
    if loai_mon in ("Canh / Súp / Lẩu", "Phở / Bún / Mì", "Kho / Rim / Om / Hầm"):
        return "nóng (theo nhóm món)"
    if loai_mon == "Gỏi / Nộm / Cuốn":
        return "nguội / mát (theo nhóm món)"
    return "Chưa nêu rõ trong nguồn gốc"


def extract_region(name: str, desc: str, tags: str) -> str:
    txt = (name + " " + desc + " " + tags).lower()
    if re.search(r"\b(hà nội|miền bắc|bắc bộ|hải phòng|nam định|thái bình|lạng sơn|tây bắc)\b", txt):
        return "Miền Bắc"
    if re.search(r"\b(huế|miền trung|quảng nam|quảng ngãi|đà nẵng|hội an|nha trang|bình định|nghệ an|thanh hóa|phan thiết|phú yên)\b", txt):
        return "Miền Trung"
    if re.search(r"\b(sài gòn|miền nam|nam bộ|miền tây|cần thơ|bến tre|sóc trăng|châu đốc|tây ninh|đồng tháp|vũng tàu)\b", txt):
        return "Miền Nam"
    return "Toàn quốc"


def extract_flavor(ing: str, desc: str) -> str:
    txt = (ing + " " + desc).lower()
    flavors = []
    if re.search(r"\b(chanh|tắc|quất|me|giấm|dấm|sấu|khế|cà chua|dưa chua|cải chua|chua)\b", txt):
        flavors.append("chua")
    if re.search(r"\b(ớt|sa tế|tiêu|gừng|riềng|cay)\b", txt):
        flavors.append("cay")
    if re.search(r"\b(nước mắm|mắm tôm|mắm nêm|mắm ruốc|nước tương|xì dầu|muối|hạt nêm|đậm đà)\b", txt):
        flavors.append("mặn đậm đà")
    if re.search(r"\b(đường|mật ong|sữa đặc|nước dừa|ngọt)\b", txt):
        flavors.append("ngọt")
    if re.search(r"\b(nước cốt dừa|bơ|phô mai|sữa tươi|kem tươi|đậu phộng|lạc|mè|vừng|béo)\b", txt):
        flavors.append("béo bùi")
    if re.search(r"\b(sả|lá chanh|húng quế|ngò gai|rau răm|tía tô|kinh giới|thì là|ngũ vị hương|quế|hồi|thảo quả)\b", txt):
        flavors.append("thơm thảo mộc")
    return ", ".join(flavors) if flavors else "hài hòa"


def extract_diet(raw_type: str, name: str, ing: str) -> str:
    low = (name + " " + ing).lower()
    if "chay" in raw_type.lower() or "chay" in name.lower():
        return "Chay"
    tags = ["Mặn"]
    if re.search(r"\b(thịt bò|bò fillet|nạm bò|gân bò|bắp bò|xương bò)\b", low):
        tags.append("Thịt bò")
    if re.search(r"\b(thịt heo|thịt lợn|ba rọi|ba chỉ|sườn heo|sườn non|nạc dăm|nạc vai|giò sống|chả lụa|giò lụa|xương heo)\b", low):
        tags.append("Thịt heo")
    if re.search(r"\b(thịt gà|cánh gà|đùi gà|ức gà|gà ta|thịt vịt|vịt)\b", low):
        tags.append("Gia cầm")
    if re.search(r"\b(tôm|mực|cá |cua|ghẹ|nghêu|ngao|sò|ốc|hàu|bạch tuộc|hải sản)\b", low):
        tags.append("Hải sản")
    return "; ".join(tags)


def load_nin_matcher() -> list[tuple[str, dict]]:
    """Optional real nutrition matching from data/raw/nin_vietnam_nutrition_mit.json (MIT)."""
    nin_path = os.path.join(RAW_DIR, "nin_vietnam_nutrition_mit.json")
    if not os.path.exists(nin_path):
        return []
    with open(nin_path, encoding="utf-8") as f:
        items = json.load(f)
    # Build concise Vietnamese ingredient keyword matcher (length >= 4 to avoid false hits)
    keywords = [
        "thịt bò", "thịt lợn", "thịt gà", "thịt vịt", "tôm", "mực", "cá chép", "cá thu", "cá hồi", "cá rô",
        "cua đồng", "đậu phụ", "trứng gà", "trứng vịt", "bánh phở", "bún", "bánh đa nem", "bánh mỳ",
        "gạo tẻ", "gạo nếp", "cà rốt", "củ cải trắng", "dưa chuột", "giá đậu xanh", "cà chua",
        "hành tây", "tỏi ta", "gừng tươi", "ớt đỏ", "nấm hương", "mộc nhĩ", "nước mắm", "lạc hạt",
        "cùi dừa", "khoai tây", "khoai lang", "bí đỏ", "mướp đắng", "rau muống", "cải bắp", "súp lơ",
    ]
    matchers = []
    for kw in keywords:
        for it in items:
            vn = clean_text(it.get("food_name_vn", "")).lower()
            if kw in vn:
                matchers.append((kw, it))
                break
    return matchers


def enrich_nin(ing_text: str, matchers: list[tuple[str, dict]]) -> dict:
    low = ing_text.lower()
    # Map southern Vietnamese synonyms to NIN terms
    low_norm = low.replace("thịt heo", "thịt lợn").replace("đậu hũ", "đậu phụ").replace("dưa leo", "dưa chuột").replace("đậu phộng", "lạc hạt").replace("bánh mì", "bánh mỳ")
    matched_names = []
    kcals, prots, fats, carbs, fibers = [], [], [], [], []
    seen = set()
    for kw, it in matchers:
        code = str(it["food_code"])
        if code in seen:
            continue
        if kw in low_norm:
            seen.add(code)
            matched_names.append(clean_text(it.get("food_name_vn", "")))
            if it.get("energy_kcal") is not None:
                kcals.append(float(it["energy_kcal"]))
            if it.get("protein_g") is not None:
                prots.append(float(it["protein_g"]))
            if it.get("fat_g") is not None:
                fats.append(float(it["fat_g"]))
            if it.get("carbohydrate_g") is not None:
                carbs.append(float(it["carbohydrate_g"]))
            if it.get("fiber_g") is not None:
                fibers.append(float(it["fiber_g"]))
    return {
        "nguyen_lieu_khop_nin": "; ".join(matched_names[:8]),
        "so_nguyen_lieu_khop_nin": len(matched_names),
        "kcal_tb_nguyen_lieu_nin_100g": round(sum(kcals) / len(kcals), 1) if kcals else "",
        "dam_tb_nin_g_100g": round(sum(prots) / len(prots), 1) if prots else "",
        "beo_tb_nin_g_100g": round(sum(fats) / len(fats), 1) if fats else "",
        "tinh_bot_tb_nin_g_100g": round(sum(carbs) / len(carbs), 1) if carbs else "",
        "chat_xo_tb_nin_g_100g": round(sum(fibers) / len(fibers), 1) if fibers else "",
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    nin_matchers = load_nin_matcher()
    print(f"[INFO] Loaded {len(nin_matchers)} NIN real nutrition matchers.")

    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        # 1. Load mnmnweb raw table to recover Cách dùng & Mách nhỏ
        mnmn_map: dict[str, dict] = {}
        mnmn_file = "A-New-Dataset-and-Empirical-Evaluation-for-Vietnamese-Food-Recommendation-System-main/Data/Raw Dataset/food_dataset_mnmnweb.csv"
        with z.open(mnmn_file) as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace")):
                key_img = clean_text(row.get("Link Ảnh", "")).lower()
                key_name = clean_text(row.get("Tên món", "")).lower()
                extra = {
                    "cach_dung": clean_text(row.get("Cách dùng", "")),
                    "mach_nho": clean_text(row.get("Mách nhỏ", "")),
                }
                if key_img:
                    mnmn_map[key_img] = extra
                if key_name:
                    mnmn_map[key_name] = extra
        print(f"[INFO] Indexed {len(mnmn_map)} mnmnweb Cách dùng/Mách nhỏ keys.")

        # 2. Read Clean Dataset/foods.csv
        foods_file = "A-New-Dataset-and-Empirical-Evaluation-for-Vietnamese-Food-Recommendation-System-main/Data/Clean Dataset/foods.csv"
        records = []
        seen_names = set()
        seen_ing_hashes = set()
        skipped_foreign = 0
        skipped_dup = 0
        skipped_short = 0

        with z.open(foods_file) as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace")):
                ten_mon = normalize_title_case(row.get("dish_name", ""))
                thanh_phan = clean_text(row.get("ingredients", ""))
                if not ten_mon or len(thanh_phan.split()) < 4:
                    skipped_short += 1
                    continue
                if FOREIGN_DISH_PAT.search(ten_mon):
                    skipped_foreign += 1
                    continue

                name_key = re.sub(r"\s+", " ", ten_mon.lower()).strip()
                ing_norm = re.sub(r"[^0-9a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]+", " ", thanh_phan.lower()).strip()
                ing_hash = hashlib.sha256(ing_norm.encode("utf-8")).hexdigest()
                if name_key in seen_names or ing_hash in seen_ing_hashes:
                    skipped_dup += 1
                    continue
                seen_names.add(name_key)
                seen_ing_hashes.add(ing_hash)

                mo_ta = clean_text(row.get("description", ""))
                cach_lam = clean_text(row.get("cooking_method", ""))
                tags = clean_text(row.get("dish_tags", ""))
                khau_phan = clean_text(row.get("serving_size", ""))
                thoi_gian = clean_text(row.get("cooking_time", ""))
                img = clean_text(row.get("image_link", ""))
                raw_type = clean_text(row.get("dish_type", ""))

                extra = mnmn_map.get(img.lower()) or mnmn_map.get(name_key) or {}
                cach_dung = extra.get("cach_dung", "")
                mach_nho = extra.get("mach_nho", "")

                loai_mon = classify_dish(ten_mon, raw_type, thanh_phan, cach_lam)
                nhiet_do = extract_serving_temp(cach_dung, cach_lam, mo_ta, loai_mon)
                vung_mien = extract_region(ten_mon, mo_ta, tags)
                huong_vi = extract_flavor(thanh_phan, mo_ta)
                che_do_an = extract_diet(raw_type, ten_mon, thanh_phan)
                nin = enrich_nin(thanh_phan, nin_matchers)

                nguon_goc = "ViFoodRec (UIT DS300 — nguồn trích: monngonmoingay)" if "monngonmoingay" in img else "ViFoodRec (UIT DS300 — nguồn trích: cooky)"

                records.append({
                    "ten_mon": ten_mon,
                    "thanh_phan": thanh_phan,
                    "loai_mon": loai_mon,
                    "nhiet_do_phuc_vu": nhiet_do,
                    "vung_mien": vung_mien,
                    "huong_vi": huong_vi,
                    "che_do_an": che_do_an,
                    "khau_phan": khau_phan,
                    "thoi_gian_nau_phut": thoi_gian,
                    "cach_dung": cach_dung,
                    "mach_nho": mach_nho,
                    "mo_ta_ngan": mo_ta[:320],
                    "tags": tags,
                    "nguyen_lieu_khop_nin": nin["nguyen_lieu_khop_nin"],
                    "so_nguyen_lieu_khop_nin": nin["so_nguyen_lieu_khop_nin"],
                    "kcal_tb_nguyen_lieu_nin_100g": nin["kcal_tb_nguyen_lieu_nin_100g"],
                    "dam_tb_nin_g_100g": nin["dam_tb_nin_g_100g"],
                    "beo_tb_nin_g_100g": nin["beo_tb_nin_g_100g"],
                    "tinh_bot_tb_nin_g_100g": nin["tinh_bot_tb_nin_g_100g"],
                    "chat_xo_tb_nin_g_100g": nin["chat_xo_tb_nin_g_100g"],
                    "nguon_du_lieu": nguon_goc,
                    "ngay_xu_ly": TODAY,
                })

    # Sort deterministically by category then dish name
    records.sort(key=lambda r: (r["loai_mon"], r["ten_mon"]))

    out_csv = os.path.join(OUT_DIR, "vietnamese_dishes.csv")
    fieldnames = [
        "dish_id",
        "ten_mon",
        "thanh_phan",
        "loai_mon",
        "nhiet_do_phuc_vu",
        "vung_mien",
        "huong_vi",
        "che_do_an",
        "khau_phan",
        "thoi_gian_nau_phut",
        "cach_dung",
        "mach_nho",
        "mo_ta_ngan",
        "tags",
        "nguyen_lieu_khop_nin",
        "so_nguyen_lieu_khop_nin",
        "kcal_tb_nguyen_lieu_nin_100g",
        "dam_tb_nin_g_100g",
        "beo_tb_nin_g_100g",
        "tinh_bot_tb_nin_g_100g",
        "chat_xo_tb_nin_g_100g",
        "nguon_du_lieu",
        "ngay_xu_ly",
    ]
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for idx, rec in enumerate(records, 1):
            rec["dish_id"] = f"VN-{idx:04d}"
            w.writerow(rec)

    print(f"[OK] Wrote {len(records)} cleaned Vietnamese dishes -> {out_csv}")
    print(f"[FILTERED] foreign={skipped_foreign}, duplicates={skipped_dup}, short/empty={skipped_short}")
    print("\n--- Breakdown by loai_mon ---")
    for k, c in Counter(r["loai_mon"] for r in records).most_common():
        print(f"  {c:4d} | {k}")
    print("\n--- Breakdown by nhiet_do_phuc_vu ---")
    for k, c in Counter(r["nhiet_do_phuc_vu"] for r in records).most_common():
        print(f"  {c:4d} | {k}")
    with_cd = sum(1 for r in records if r["cach_dung"])
    with_nin = sum(1 for r in records if r["so_nguyen_lieu_khop_nin"] > 0)
    print(f"\n[STATS] With Cách dùng: {with_cd}/{len(records)} | With real NIN nutrition match: {with_nin}/{len(records)}")


if __name__ == "__main__":
    main()
