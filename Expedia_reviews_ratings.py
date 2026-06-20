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

# ============================================
# Chrome driver setup
# ============================================
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--start-maximized")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# ============================================
# Helper functions
# ============================================
def random_delay(min_sec=2, max_sec=4):
    time.sleep(random.uniform(min_sec, max_sec))

def safe_save(df, primary_path):
    """Try to save to primary path; if permission denied, save to fallback."""
    try:
        df.to_csv(primary_path, index=False)
        print(f"  💾 Saved to {primary_path}")
        return True
    except PermissionError:
        fallback_path = os.path.join(os.getcwd(), "expedia_results_fallback.csv")
        df.to_csv(fallback_path, index=False)
        print(f"  ⚠️ Permission denied for {primary_path}.")
        print(f"  💾 Saved to fallback: {fallback_path}")
        return False

def extract_expedia_rating_reviews_from_google(hotel_name):
    """Extract rating and review count from Google snippet only (no Expedia page)."""
    print(f"\n🔍 Searching Google for: expedia {hotel_name}")
    
    try:
        search_query = f"expedia {hotel_name} rating"
        url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        driver.get(url)
        random_delay(3, 5)
        
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        rating = "N/A"
        review_count = "N/A"
        
        # Rating patterns
        rating_patterns = [
            r'Rating[:\s]*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*/\s*5',
            r'(\d+\.?\d*)\s*out of\s*5',
            r'(\d+\.?\d*)\s*star',
            r'(\d+\.?\d*)\s*·\s*',
        ]
        for pattern in rating_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                rating = match.group(1)
                print(f"  ✅ Rating found: {rating}")
                break
        
        # Review count patterns
        count_patterns = [
            r'([\d,]+)\s*reviews?',
            r'([\d,]+)\s*Ratings?',
            r'([\d,]+)\s*guest\s*reviews?',
            r'Based\s+on\s+([\d,]+)\s+reviews?',
        ]
        for pattern in count_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                review_count = match.group(1).replace(',', '')
                print(f"  ✅ Review count found: {review_count}")
                break
        
        return rating, review_count
        
    except Exception as e:
        print(f"  ❌ Error during Google search: {e}")
        return "N/A", "N/A"

def read_hotels_from_excel(file_path, sheet_name=0, column_name='Hotel Name'):
    try:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return []
        if file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        elif file_path.endswith('.xls'):
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            print("❌ Unsupported file format. Use .xlsx or .xls")
            return []
        if column_name not in df.columns:
            print(f"❌ Column '{column_name}' not found. Available: {list(df.columns)}")
            return []
        hotels = df[column_name].dropna().tolist()
        hotels = [str(h).strip() for h in hotels]
        print(f"✅ Loaded {len(hotels)} hotels from '{file_path}'")
        print(f"📋 First 5 hotels: {hotels[:5]}{'...' if len(hotels) > 5 else ''}")
        return hotels
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return []

# ============================================
# CONFIGURATION
# ============================================
EXCEL_FILE_PATH = r"C:/Users/Administrator/Desktop/RatingsProject/property_files/Shobhit_Property_List.xlsx"
SHEET_NAME = 0
HOTEL_COLUMN_NAME = "Hotel Name"
OUTPUT_CSV_FILE = r"C:/Users/Administrator/Desktop/RatingsProject/Results/Shobhit_Property_List_expedia_results.csv"

# Create output directory if needed
output_dir = os.path.dirname(OUTPUT_CSV_FILE)
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"📁 Created directory: {output_dir}")

print("="*60)
print("EXPEDIA SCRAPER (Google snippet only, no CAPTCHA)")
print("="*60)

hotels = read_hotels_from_excel(EXCEL_FILE_PATH, SHEET_NAME, HOTEL_COLUMN_NAME)
if not hotels:
    print("❌ No hotels found. Exiting.")
    driver.quit()
    exit()

print(f"\n🚀 Starting scraping for {len(hotels)} hotels...")

results = []

try:
    for i, hotel in enumerate(hotels, 1):
        print(f"\n{'='*60}")
        print(f"Progress: {i}/{len(hotels)} - {hotel}")
        print('='*60)
        
        rating, review_count = extract_expedia_rating_reviews_from_google(hotel)
        
        results.append({
            "Hotel Name": hotel,
            "Rating": rating,
            "Review Count": review_count
        })
        
        print(f"  📊 {hotel}: Rating = {rating}, Review Count = {review_count}")
        
        # Save after each hotel using safe_save (handles permission errors)
        safe_save(pd.DataFrame(results), OUTPUT_CSV_FILE)
        
        if i < len(hotels):
            delay = random.uniform(8, 12)
            print(f"  ⏳ Waiting {delay:.1f} seconds...")
            time.sleep(delay)
    
    # Final saves with timestamp
    final_df = pd.DataFrame(results)
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    final_df.to_csv(f"expedia_google_snippet_{timestamp}.csv", index=False)
    final_df.to_excel(f"expedia_google_snippet_{timestamp}.xlsx", index=False)
    print(f"\n✅ Done! Final results saved as CSV and Excel with timestamp.")

except KeyboardInterrupt:
    print("\n⚠️ Interrupted! Saving partial results...")
    if results:
        pd.DataFrame(results).to_csv("expedia_partial.csv", index=False)
        pd.DataFrame(results).to_excel("expedia_partial.xlsx", index=False)
        print("💾 Saved partial results.")
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    if results:
        pd.DataFrame(results).to_csv("expedia_partial.csv", index=False)
        pd.DataFrame(results).to_excel("expedia_partial.xlsx", index=False)
        print("💾 Saved partial results.")
finally:
    driver.quit()
    print("👋 Browser closed.")