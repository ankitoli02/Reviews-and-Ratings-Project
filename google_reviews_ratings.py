import os
import re
import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ================== CONFIGURATION ==================
EXCEL_FILE_PATH = r"C:/Users/Administrator/Desktop/RatingsProject/property_files/EcoHotels.xlsx"
OUTPUT_CSV_FILE = r"C:/Users/Administrator/Desktop/RatingsProject/Results/ECo_google_results.csv"
SHEET_NAME = 0                     # 0 means first sheet; change if needed
HOTEL_COLUMN_NAME = "Hotel Name"   # exact column name in your Excel

# Scraping behaviour
MIN_DELAY_BETWEEN_QUERIES = 10     # seconds
MAX_DELAY_BETWEEN_QUERIES = 18
RANDOM_DELAY_AFTER_LOAD = (4, 6)   # seconds after page loads

# ================== SETUP CHROME WITH STEALTH ==================
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--start-maximized")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

def random_sleep(min_sec=2, max_sec=4):
    time.sleep(random.uniform(min_sec, max_sec))

def extract_rating_and_reviews(hotel_name):
    """Search Google for the hotel and extract rating & review count."""
    query = f"{hotel_name} hotel"
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    driver.get(search_url)
    random_sleep(*RANDOM_DELAY_AFTER_LOAD)

    # Scroll a little to trigger lazy-loaded content
    driver.execute_script("window.scrollTo(0, 400);")
    random_sleep(1, 2)

    rating = "N/A"
    reviews = "N/A"

    # ----- 1. Try aria-label (most reliable for rating) -----
    try:
        elements = driver.find_elements(By.XPATH, "//*[@aria-label]")
        for elem in elements:
            aria = elem.get_attribute("aria-label").lower()
            # pattern: "Rated 4.7 out of 5 stars"
            match = re.search(r'rated\s*(\d+\.?\d*)\s*out\s*of\s*5', aria)
            if match:
                rating = match.group(1)
                break
            # pattern: "4.7 stars"
            match = re.search(r'(\d+\.?\d*)\s*stars?', aria)
            if match:
                rating = match.group(1)
                break
    except:
        pass

    # ----- 2. Try known Google rating CSS classes -----
    if rating == "N/A":
        rating_classes = [
            "Aq14fc",      # observed class for rating number
            "fzvQIb",      # alternative
            "iHxmLe",      # star container
            "BHMmbe",      # knowledge panel score
            "gglh5d",      # sometimes used
            "ZkP5Je",      # another observed class
        ]
        for cls in rating_classes:
            try:
                elem = driver.find_element(By.CSS_SELECTOR, f".{cls}")
                text = elem.text
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    rating = match.group(1)
                    break
            except:
                continue

    # ----- 3. Regex on full page text (last resort) -----
    if rating == "N/A":
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            patterns = [
                r'(\d+\.?\d*)\s*[★☆]{4,5}',          # 4.7★★★★★
                r'(\d+\.?\d*)\s*out of 5',            # 4.7 out of 5
                r'(\d+\.?\d*)\s*·',                   # 4.7 · (1,234 reviews)
                r'(\d+\.?\d*)\s*stars?',              # 4.7 stars
                r'Rating:\s*(\d+\.?\d*)',             # Rating: 4.7
            ]
            for pat in patterns:
                match = re.search(pat, body_text, re.IGNORECASE)
                if match:
                    rating = match.group(1)
                    break
        except:
            pass

    # ----- Extract review count (multiple methods) -----
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        review_patterns = [
            r'([\d,]+)\s*Google\s*reviews?',
            r'([\d,]+)\s*reviews?',
            r'([\d,]+)\s*Ratings?',
            r'\(([\d,]+)\)\s*reviews?',
            r'([\d.]+[Kk])\s*reviews?',
        ]
        for pat in review_patterns:
            match = re.search(pat, body_text, re.IGNORECASE)
            if match:
                raw = match.group(1)
                if 'K' in raw.upper():
                    num = float(raw.replace('K', '').replace('k', ''))
                    reviews = str(int(num * 1000))
                else:
                    reviews = raw.replace(',', '')
                break
    except:
        pass

    # If still missing, look for element containing "reviews"
    if reviews == "N/A":
        try:
            review_elem = driver.find_element(By.XPATH, "//*[contains(text(), 'reviews') or contains(text(), 'Reviews')]")
            match = re.search(r'([\d,]+)\s*reviews?', review_elem.text, re.IGNORECASE)
            if match:
                reviews = match.group(1).replace(',', '')
        except:
            pass

    return rating, reviews

# ================== MAIN SCRIPT ==================
def main():
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(OUTPUT_CSV_FILE)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created output directory: {output_dir}")

    # Read Excel file
    print(f"📂 Reading Excel: {EXCEL_FILE_PATH}")
    try:
        df = pd.read_excel(EXCEL_FILE_PATH, sheet_name=SHEET_NAME)
        if HOTEL_COLUMN_NAME not in df.columns:
            raise ValueError(f"Column '{HOTEL_COLUMN_NAME}' not found. Available: {list(df.columns)}")
        hotels = df[HOTEL_COLUMN_NAME].dropna().astype(str).str.strip().tolist()
        print(f"✅ Loaded {len(hotels)} hotels.")
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
        driver.quit()
        return

    results = []
    total = len(hotels)

    for idx, hotel in enumerate(hotels, start=1):
        print(f"\n[{idx}/{total}] Processing: {hotel}")
        rating, reviews = extract_rating_and_reviews(hotel)
        print(f"   → Rating: {rating}  |  Reviews: {reviews}")

        results.append({
            "Hotel Name": hotel,
            "Google Rating": rating,
            "Google Review Count": reviews,
        })

        # Save incrementally after each hotel
        pd.DataFrame(results).to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
        print(f"   💾 Saved to {OUTPUT_CSV_FILE}")

        # Wait between queries to avoid being blocked
        if idx < total:
            delay = random.uniform(MIN_DELAY_BETWEEN_QUERIES, MAX_DELAY_BETWEEN_QUERIES)
            print(f"   ⏳ Waiting {delay:.1f} seconds...")
            time.sleep(delay)

    # Final summary
    print("\n" + "="*60)
    print("✅ COMPLETED")
    print("="*60)
    ratings_found = sum(1 for r in results if r['Google Rating'] != 'N/A')
    reviews_found = sum(1 for r in results if r['Google Review Count'] != 'N/A')
    print(f"📊 Success rate: Ratings {ratings_found}/{total} ({ratings_found/total*100:.1f}%)")
    print(f"                Reviews {reviews_found}/{total} ({reviews_found/total*100:.1f}%)")
    print(f"\n📁 Output file: {OUTPUT_CSV_FILE}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user. Partial results saved.")
    finally:
        driver.quit()
        print("👋 Browser closed.")