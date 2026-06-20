from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import pandas as pd
import re
import os

# ---------- Chrome stealth setup ----------
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--start-maximized")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

def random_delay(min_sec=2, max_sec=4):
    time.sleep(random.uniform(min_sec, max_sec))

# ---------- Step 1: Find Agoda hotel page via Google ----------
def find_agoda_page_via_google(hotel_name):
    print(f"  🔍 Google search: agoda {hotel_name}")
    query = f"agoda {hotel_name}"
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    driver.get(url)
    random_delay(3, 5)
    
    agoda_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'agoda.com')]")
    for link in agoda_links:
        href = link.get_attribute("href")
        if href and "agoda.com" in href and "/hotel/" in href:
            print(f"  ✅ Found Agoda page: {href[:80]}...")
            return href
    return None

# ---------- Step 2: Extract rating & reviews ----------
def extract_from_agoda_page(agoda_url):
    if not agoda_url:
        return "N/A", "N/A"
    
    print(f"  🌐 Opening Agoda page: {agoda_url[:80]}...")
    driver.get(agoda_url)
    random_delay(5, 7)
    
    driver.execute_script("window.scrollTo(0, 300);")
    random_delay(2, 3)
    driver.execute_script("window.scrollTo(0, 600);")
    random_delay(2, 3)
    
    rating = "N/A"
    review_count = "N/A"
    
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        page_html = driver.page_source
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Rating extraction (same as before)
        rating_selectors = [
            "[data-selenium='review-score']", "[class*='ReviewScore']", "[class*='review-score']",
            ".Review__score", ".score-rating", "[itemprop='ratingValue']", ".PropertyRating__score"
        ]
        for selector in rating_selectors:
            try:
                elem = driver.find_element(By.CSS_SELECTOR, selector)
                match = re.search(r'(\d+\.?\d*)', elem.text)
                if match:
                    rating = match.group(1)
                    print(f"  ✅ Rating found via CSS: {rating}/10")
                    break
            except:
                pass
        
        if rating == "N/A":
            try:
                elem = driver.find_element(By.XPATH, "//*[contains(text(), 'out of 10') or contains(text(), '/10')]")
                match = re.search(r'(\d+\.?\d*)\s*[/out of]+', elem.text, re.IGNORECASE)
                if match:
                    rating = match.group(1)
                    print(f"  ✅ Rating found via XPath: {rating}/10")
            except:
                pass
        
        if rating == "N/A":
            patterns = [r'(\d+\.?\d*)\s*/\s*10', r'(\d+\.?\d*)\s*out of 10', r'Rating:\s*(\d+\.?\d*)',
                        r'Score:\s*(\d+\.?\d*)', r'(\d+\.?\d*)\s*★', r'<span[^>]*class="[^"]*score[^"]*"[^>]*>(\d+\.?\d*)</span>']
            for pat in patterns:
                match = re.search(pat, page_html, re.IGNORECASE | re.DOTALL)
                if match:
                    rating = match.group(1)
                    print(f"  ✅ Rating found via regex: {rating}/10")
                    break
        
        # Review count extraction
        review_patterns = [r'([\d,]+)\s*reviews?', r'([\d,]+)\s*Ratings?', r'based on\s+([\d,]+)\s+reviews?',
                           r'\(([\d,]+)\)\s*reviews?', r'([\d,]+)\s*Guest\s+reviews?', r'([\d,]+)\s*verified\s+reviews?']
        for pat in review_patterns:
            match = re.search(pat, page_text, re.IGNORECASE)
            if match:
                review_count = match.group(1).replace(',', '')
                print(f"  ✅ Review count found: {review_count}")
                break
        
        if review_count == "N/A":
            try:
                elems = driver.find_elements(By.XPATH, "//*[contains(text(), 'review') or contains(text(), 'Review')]")
                for elem in elems:
                    match = re.search(r'([\d,]+)\s*reviews?', elem.text, re.IGNORECASE)
                    if match and int(match.group(1).replace(',', '')) > 10:
                        review_count = match.group(1).replace(',', '')
                        print(f"  ✅ Review count via XPath: {review_count}")
                        break
            except:
                pass
        
        if review_count == "N/A":
            for pat in review_patterns:
                match = re.search(pat, page_html, re.IGNORECASE)
                if match:
                    review_count = match.group(1).replace(',', '')
                    print(f"  ✅ Review count via HTML regex: {review_count}")
                    break
        
        if rating == "N/A" and review_count == "N/A":
            print("  ⚠️ Could not extract data.")
        
        return rating, review_count
    except Exception as e:
        print(f"  ❌ Error during extraction: {e}")
        return "N/A", "N/A"

def process_hotel(hotel_name):
    print(f"\n🔍 Processing: {hotel_name}")
    agoda_url = find_agoda_page_via_google(hotel_name)
    if not agoda_url:
        print("  ❌ No Agoda page found.")
        return "N/A", "N/A"
    return extract_from_agoda_page(agoda_url)

def read_hotels_from_excel(file_path, sheet_name=0, column_name='Hotel Name'):
    try:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return []
        if file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            print("❌ Unsupported file format.")
            return []
        if column_name not in df.columns:
            print(f"❌ Column '{column_name}' not found. Available: {list(df.columns)}")
            return []
        hotels = df[column_name].dropna().tolist()
        hotels = [str(h).strip() for h in hotels]
        print(f"✅ Loaded {len(hotels)} hotels")
        return hotels
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
        return []

# ---------- Main ----------
EXCEL_FILE_PATH = r"C:/Users/Administrator/Desktop/RatingsProject/property_files/Shobhit_Property_List.xlsx"
OUTPUT_CSV_FILE = r"C:/Users/Administrator/Desktop/RatingsProject/Results/Shobhit_Property_List_agoda_results.csv"
SHEET_NAME = 0
HOTEL_COLUMN_NAME = "Hotel Name"

output_dir = os.path.dirname(OUTPUT_CSV_FILE)
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir)

print("="*60)
print("AGODA SCRAPER - Incremental save to single CSV")
print("="*60)
print(f"\n📁 Input: {EXCEL_FILE_PATH}")
print(f"📁 Output (single file): {OUTPUT_CSV_FILE}")

hotels = read_hotels_from_excel(EXCEL_FILE_PATH, SHEET_NAME, HOTEL_COLUMN_NAME)
if not hotels:
    print("❌ No hotels found. Exiting.")
    driver.quit()
    exit()

results = []
try:
    for i, hotel in enumerate(hotels, 1):
        print(f"\n{'='*60}")
        print(f"Progress: {i}/{len(hotels)} - {hotel}")
        print('='*60)
        
        rating, reviews = process_hotel(hotel)
        results.append({
            "Hotel Name": hotel,
            "Rating (out of 10)": rating,
            "Review Count": reviews,
            "Platform": "Agoda"
        })
        
        # ✅ Incremental save: overwrite the same CSV file after each hotel
        pd.DataFrame(results).to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
        print(f"  💾 Saved to {OUTPUT_CSV_FILE} (updated)")
        
        print(f"  📊 FINAL: {hotel} → Rating={rating}/10, Reviews={reviews}")
        
        if i < len(hotels):
            delay = random.uniform(12, 18)
            print(f"  ⏳ Waiting {delay:.0f} seconds...")
            time.sleep(delay)
    
    # Final summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    ratings_found = sum(1 for r in results if r['Rating'] != 'N/A')
    reviews_found = sum(1 for r in results if r['Review Count'] != 'N/A')
    print(f"\n📊 Success: Ratings {ratings_found}/{len(results)} ({ratings_found/len(results)*100:.1f}%)")
    print(f"          Review counts {reviews_found}/{len(results)} ({reviews_found/len(results)*100:.1f}%)")
    print(f"\n✅ Done! Single output file: {OUTPUT_CSV_FILE}")

except KeyboardInterrupt:
    print("\n⚠️ Interrupted – saving current results to same file...")
    if results:
        pd.DataFrame(results).to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
        print(f"   Saved partial results to {OUTPUT_CSV_FILE}")
except Exception as e:
    print(f"\n❌ Error: {e}")
    if results:
        pd.DataFrame(results).to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
        print(f"   Saved data up to error to {OUTPUT_CSV_FILE}")
finally:
    driver.quit()
    print("👋 Browser closed")