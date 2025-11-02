import pandas as pd
import requests
from urllib.parse import quote

# -------------------------------
# تابع دریافت قیمت از دیجی‌کالا
# -------------------------------
def get_price_from_digikala(product_name):
    try:
        search_url = f"https://api.digikala.com/v1/search/?q={quote(product_name)}"
        response = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        data = response.json()
        products = data.get("data", {}).get("products", [])
        if not products:
            return None
        
        first = products[0]
        title = first["title_fa"]
        price = first.get("default_variant", {}).get("price", {}).get("selling_price", None)
        if price:
            return price
        return None
    except Exception as e:
        print(f"❌ خطا برای {product_name}: {e}")
        return None

# -------------------------------
# از اینجا به بعد کدهای قبلیت میاد
# -------------------------------

# فایل‌ها رو می‌خونیم
jonoobmall = pd.read_csv("jonoobmall.csv")
kalakhane = pd.read_csv("kalakhane.csv")
dehshikhstore = pd.read_csv("dehshikhstore.csv")

# ادغام اولیه
all_data = pd.concat([jonoobmall, kalakhane, dehshikhstore], ignore_index=True)
print("تعداد کل ردیف‌ها:", len(all_data))

# مرحله ۴: یکی‌سازی ستون‌ها
# (کدهای قبلیت برای rename و پاکسازی همونجا بمونن)

# مرحله ۵: حذف تکراری‌ها
# (کد مربوط به drop_duplicates همونجا بمونه)

# -------------------------------
# مرحله ۶: به‌روزرسانی قیمت از دیجی‌کالا
# -------------------------------
updated = 0
for i, row in all_data.iterrows():
    title = row['title']
    new_price = get_price_from_digikala(title)
    if new_price:
        all_data.at[i, 'price'] = new_price
        updated += 1

print(f"💰 قیمت {updated} محصول از دیجی‌کالا به‌روزرسانی شد.")
