from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import pandas as pd
import re
import os

# ------------------------------
# Chrome stealth setup
# ------------------------------
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--start-maximized")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# ------------------------------
# Helper functions
# ------------------------------
def random_delay(min_sec=2, max_sec=4):
    time.sleep(random.uniform(min_sec, max_sec))

def safe_save(df, primary_path):
    try:
        df.to_csv(primary_path, index=False)
        print(f"  💾 Saved to {primary_path}")
    except PermissionError:
        fallback = os.path.join(os.getcwd(), "mmt_results_fallback.csv")
        df.to_csv(fallback, index=False)
        print(f"  ⚠️ Permission denied. Saved to {fallback}")

def extract_mmt_from_google_snippet(hotel_name):
    """
    Search Google: site:makemytrip.com <hotel_name> rating
    Extract rating and review count from the snippet (as shown in your screenshot).
    """
    print(f"\n🔍 Searching Google (MMT) for: {hotel_name}")
    search_query = f"site:makemytrip.com {hotel_name} rating"
    url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
    
    try:
        driver.get(url)
        random_delay(3, 5)
        
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        rating = "N/A"
        review_count = "N/A"
        
        # ----- Rating extraction -----
        # Patterns that match "4.3" from snippets like "4.3 ★★★★★" or "4.3/5" or "Rating: 4.3"
        rating_patterns = [
            r'(\d+\.?\d*)\s*[★☆]',           # 4.3 ★★★★★
            r'(\d+\.?\d*)\s*/\s*5',           # 4.3/5
            r'Rating[:\s]*(\d+\.?\d*)',        # Rating: 4.3
            r'(\d+\.?\d*)\s*out of 5',        # 4.3 out of 5
        ]
        for pat in rating_patterns:
            match = re.search(pat, page_text, re.IGNORECASE)
            if match:
                rating = match.group(1)
                print(f"  ✅ Rating: {rating}")
                break
        
        # ----- Review count extraction -----
        # Patterns that match "877" from snippets like "877 reviews" or "877 Google reviews" or "(877)"
        count_patterns = [
            r'([\d,]+)\s+reviews?',            # 877 reviews
            r'([\d,]+)\s+Google\s+reviews?',   # 877 Google reviews
            r'\(([\d,]+)\)',                   # (877)
            r'([\d,]+)\s+Ratings?',            # 877 Ratings
        ]
        for pat in count_patterns:
            match = re.search(pat, page_text, re.IGNORECASE)
            if match:
                review_count = match.group(1).replace(',', '')
                print(f"  ✅ Review count: {review_count}")
                break
        
        return rating, review_count
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return "N/A", "N/A"

def read_hotels_from_excel(file_path, sheet_name=0, column_name='Hotel Name'):
    try:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return []
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        if column_name not in df.columns:
            print(f"❌ Column '{column_name}' not found. Available: {list(df.columns)}")
            return []
        hotels = df[column_name].dropna().tolist()
        hotels = [str(h).strip() for h in hotels]
        print(f"✅ Loaded {len(hotels)} hotels")
        return hotels
    except Exception as e:
        print(f"❌ Excel error: {e}")
        return []

# ------------------------------
# CONFIGURATION
# ------------------------------
EXCEL_FILE_PATH = r"C:/Users/Administrator/Desktop/RatingsProject/property_files/Shobhit_Property_List.xlsx"
HOTEL_COLUMN_NAME = "Hotel Name"
OUTPUT_CSV = r"C:/Users/Administrator/Desktop/RatingsProject/Results/Shobhit_Property_List_mmt_results.csv"

os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

print("="*60)
print("MAKEMYTRIP (MMT) EXTRACTOR - Google Snippet (No CAPTCHA)")
print("="*60)

hotels = read_hotels_from_excel(EXCEL_FILE_PATH, 0, HOTEL_COLUMN_NAME)
if not hotels:
    driver.quit()
    exit()

results = []

for i, hotel in enumerate(hotels, 1):
    print(f"\n--- {i}/{len(hotels)} : {hotel} ---")
    rating, reviews = extract_mmt_from_google_snippet(hotel)
    results.append({
        "Hotel Name": hotel,
        "Rating": rating,
        "Review Count": reviews
    })
    print(f"  => Rating: {rating}, Reviews: {reviews}")
    
    # Save incrementally
    safe_save(pd.DataFrame(results), OUTPUT_CSV)
    
    if i < len(hotels):
        delay = random.uniform(8, 12)
        print(f"  ⏳ Waiting {delay:.1f} sec...")
        time.sleep(delay)

# Final backup with timestamp
final_df = pd.DataFrame(results)
timestamp = time.strftime('%Y%m%d_%H%M%S')
final_df.to_csv(f"mmt_google_snippet_{timestamp}.csv", index=False)
final_df.to_excel(f"mmt_google_snippet_{timestamp}.xlsx", index=False)
print(f"\n✅ Done! Results saved to {OUTPUT_CSV} and timestamped files.")
driver.quit()