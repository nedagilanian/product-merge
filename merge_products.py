import pandas as pd
import requests
from urllib.parse import quote
import time

# === 1. خواندن فایل‌های CSV ===
jonoobmall = pd.read_csv("jonoobmall.csv")
kalakhane = pd.read_csv("kalakhane.csv")
dehshikhstore = pd.read_csv("dehshikhstore.csv")

print("تعداد کل ردیف‌ها:", len(jonoobmall) + len(kalakhane) + len(dehshikhstore))

# === 2. یکسان‌سازی نام ستون‌ها ===
rename_map = {
    'نام': 'title',
    'نام محصول': 'title',
    'نام کالا': 'title',
    'product_name': 'title',
    'قیمت': 'price',
    'قیمت اصلی': 'price',
    'قیمت فروش فوق‌العاده': 'sale_price',
    'برند': 'brand',
    'برندها': 'brand',
    'توضیحات': 'description',
    'توضیح کوتاه': 'short_desc',
    'تصاویر': 'images'
}

for df in [jonoobmall, kalakhane, dehshikhstore]:
    df.rename(columns=rename_map, inplace=True)

# بررسی اینکه ستون title در همه فایل‌ها وجود دارد
for df_name, df in [("jonoobmall", jonoobmall), ("kalakhane", kalakhane), ("dehshikhstore", dehshikhstore)]:
    if 'title' not in df.columns:
        print(f"❌ فایل {df_name} ستون title ندارد! لطفاً بررسی شود.")
        raise SystemExit

# === 3. ادغام داده‌ها ===
all_data = pd.concat([jonoobmall, kalakhane, dehshikhstore], ignore_index=True)
print("✅ ستون‌های نهایی:", list(all_data.columns))

# === 4. حذف محصولات تکراری ===
before = len(all_data)
all_data.drop_duplicates(subset=['title'], inplace=True)
print(f"🧹 محصولات تکراری حذف شدند: {before - len(all_data)} مورد")
print(f"🔢 تعداد محصولات نهایی: {len(all_data)}")

# === 5. تابع دریافت قیمت از دیجی‌کالا ===
def get_price_from_digikala(product_name):
    try:
        url = f"https://api.digikala.com/v1/search/?q={quote(product_name)}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = res.json()
        products = data.get("data", {}).get("products", [])
        if not products:
            return None
        return products[0].get("default_variant", {}).get("price", {}).get("selling_price")
    except Exception as e:
        print(f"❌ خطا هنگام دریافت قیمت برای {product_name}: {e}")
        return None

# === 6. تابع دریافت توضیحات و ویژگی‌ها از دیجی‌کالا ===
def get_product_details_from_digikala(product_name):
    try:
        # مرحله ۱: جستجوی محصول
        search_url = f"https://api.digikala.com/v1/search/?q={quote(product_name)}"
        response = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        data = response.json()
        products = data.get("data", {}).get("products", [])
        if not products:
            return None, None

        # گرفتن شناسه محصول
        product_id = products[0].get("id")
        if not product_id:
            return None, None

        # مرحله ۲: دریافت جزئیات محصول
        details_url = f"https://api.digikala.com/v1/product/{product_id}/"
        details_res = requests.get(details_url, headers={'User-Agent': 'Mozilla/5.0'})
        details_data = details_res.json()

        product_data = details_data.get("data", {}).get("product", {})

        # استخراج توضیحات
        desc = product_data.get("review", {}).get("description", "")
        if not desc:
            desc = product_data.get("seo_meta", {}).get("description", "")

        # استخراج ویژگی‌ها
        specs = product_data.get("specifications", [])
        specs_text = ""
        for group in specs:
            for attr in group.get("attributes", []):
                name = attr.get("title_fa", "") or attr.get("title_en", "")
                values = [v.get("title", "") for v in attr.get("values", [])]
                if name and values:
                    specs_text += f"{name}: {'، '.join(values)}\n"

        return desc.strip(), specs_text.strip()

    except Exception as e:
        print(f"❌ خطا هنگام واکشی توضیحات برای {product_name}: {e}")
        return None, None

# === 7. بروزرسانی قیمت و توضیحات ===
updated_prices = []
updated_descs = []
updated_specs = []

print("🚀 شروع بروزرسانی محصولات از دیجی‌کالا...")

for index, row in all_data.iterrows():
    title = str(row.get('title', '')).strip()
    if not title:
        print(f"⚠️ ردیف {index} بدون عنوان است، رد شد.")
        continue

    # دریافت قیمت
    new_price = get_price_from_digikala(title)
    updated_prices.append(new_price if new_price else row.get('price', None))

    # دریافت توضیحات و ویژگی‌ها (فقط اگر توضیح ناقص است)
    desc, specs = None, None
    if pd.isna(row.get('description')) or len(str(row.get('description')).strip()) < 20:
        desc, specs = get_product_details_from_digikala(title)

    updated_descs.append(desc if desc else row.get('description', ''))
    updated_specs.append(specs if specs else "")

    print(f"{index+1}/{len(all_data)} | {title[:40]} → 💰 {new_price if new_price else '❌'} | 📝 توضیح: {'✅' if desc else '❌'}")

    time.sleep(1.5)  # جلوگیری از بلاک شدن توسط سرور دیجی‌کالا

# === 8. افزودن داده‌ها به دیتافریم ===
all_data['digikala_price'] = updated_prices
all_data['digikala_description'] = updated_descs
all_data['digikala_specs'] = updated_specs

# === 9. ذخیره فایل نهایی ===
output_name = "final_products_with_digikala.csv"
all_data.to_csv(output_name, index=False, encoding='utf-8-sig')
print(f"💾 فایل نهایی ذخیره شد: {output_name} ✅")
