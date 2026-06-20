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

# ---------- Step 1: Find TripAdvisor hotel page via Google ----------
def find_tripadvisor_page_via_google(hotel_name):
    """Search Google for 'tripadvisor hotel_name' and return the first TripAdvisor result URL."""
    print(f"  🔍 Google search: tripadvisor {hotel_name}")
    query = f"tripadvisor {hotel_name}"
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    driver.get(url)
    random_delay(3, 5)

    ta_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'tripadvisor.com')]")
    for link in ta_links:
        href = link.get_attribute("href")
        if href and "tripadvisor.com" in href and "/Hotel_Review-" in href:
            print(f"  ✅ Found TripAdvisor page: {href[:80]}...")
            return href
    return None

# ---------- Step 2: Extract rating & reviews from TripAdvisor hotel page (improved) ----------
def extract_from_tripadvisor_page(ta_url):
    """Navigate to a TripAdvisor hotel page and scrape rating (before green dots) & review count."""
    if not ta_url:
        return "N/A", "N/A"

    print(f"  🌐 Opening TripAdvisor page: {ta_url[:80]}...")
    driver.get(ta_url)
    random_delay(6, 8)

    # Scroll to trigger lazy loading
    driver.execute_script("window.scrollTo(0, 500);")
    random_delay(2, 3)
    driver.execute_script("window.scrollTo(0, 1000);")
    random_delay(2, 3)

    rating = "N/A"
    review_count = "N/A"

    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Get full page source and visible text
        page_source = driver.page_source
        page_text = driver.find_element(By.TAG_NAME, "body").text

        # ----- RATING EXTRACTION (specifically the number before green dots) -----
        # TripAdvisor often shows rating like "4.7 (1,331 reviews)"
        # We need to capture the numeric part before the parentheses or the word "reviews"
        rating_patterns = [
            # Match pattern: number then space then (number reviews) - captures the first number
            r'(\d+(?:\.\d+)?)\s*\(\d+[\d,]*\s*reviews?\)',
            # Match: number then directly a space and "review" or "reviews"
            r'(\d+(?:\.\d+)?)\s*reviews?',
            # Match: number with a possible decimal, followed by optional space and then a green dot indicator (if any)
            r'(\d+(?:\.\d+)?)\s*(?=\(?[\d,]*\s*reviews?)',
            # General pattern: bubble rating in a specific element
            r'data-test-target="review-rating"[^>]*>(\d+(?:\.\d+)?)</span>',
            r'bubble_rating\D*(\d+(?:\.\d+)?)',
            r'aria-label="[^"]*(\d+(?:\.\d+)?)\s*out of 5[^"]*"',
        ]

        for pat in rating_patterns:
            # Search in visible text first
            match = re.search(pat, page_text, re.IGNORECASE)
            if match:
                rating = match.group(1)
                print(f"  ✅ Rating found: {rating}/5 (before green dots)")
                break
            # If not found, search in full HTML source
            match = re.search(pat, page_source, re.IGNORECASE)
            if match:
                rating = match.group(1)
                print(f"  ✅ Rating found (HTML): {rating}/5")
                break

        # Special case: look for an element containing both number and "reviews"
        if rating == "N/A":
            try:
                # Find elements that contain something like "4.7 (1,331 reviews)"
                possible_divs = driver.find_elements(By.XPATH, "//*[contains(text(), '(') and contains(text(), 'reviews')]")
                for div in possible_divs:
                    text = div.text
                    # Extract the number right before an opening parenthesis
                    match = re.search(r'(\d+(?:\.\d+)?)\s*\(', text)
                    if match:
                        rating = match.group(1)
                        print(f"  ✅ Rating found via parenthesized reviews: {rating}")
                        break
            except:
                pass

        # ----- REVIEW COUNT EXTRACTION (unchanged but improved) -----
        review_patterns = [
            r'([\d,]+)\s*reviews?',
            r'([\d,]+)\s*Reviews',
            r'([\d,]+)\s*ratings?',
            r'Based on\s+([\d,]+)\s+reviews',
            r'<span[^>]*class="[^"]*review-count[^"]*"[^>]*>([\d,]+)</span>',
            r'\(([\d,]+)\s*reviews?\)',
        ]

        for pat in review_patterns:
            match = re.search(pat, page_text, re.IGNORECASE)
            if match:
                review_count = match.group(1).replace(',', '')
                print(f"  ✅ Review count found: {review_count}")
                break

        # If still no review count, try HTML source
        if review_count == "N/A":
            for pat in review_patterns:
                match = re.search(pat, page_source, re.IGNORECASE)
                if match:
                    review_count = match.group(1).replace(',', '')
                    print(f"  ✅ Review count found (HTML): {review_count}")
                    break

        # Fallback: try to find the "About" section which often contains rating/review data
        if rating == "N/A" or review_count == "N/A":
            try:
                about_tab = driver.find_element(By.XPATH, "//*[contains(@data-automation, 'aboutTab') or contains(text(), 'About')]")
                about_tab.click()
                random_delay(3, 4)
                page_source = driver.page_source
                page_text = driver.find_element(By.TAG_NAME, "body").text
                # Re-run rating and review extraction
                for pat in rating_patterns:
                    match = re.search(pat, page_text, re.IGNORECASE)
                    if match and rating == "N/A":
                        rating = match.group(1)
                        break
                for pat in review_patterns:
                    match = re.search(pat, page_text, re.IGNORECASE)
                    if match and review_count == "N/A":
                        review_count = match.group(1).replace(',', '')
                        break
            except:
                pass

        return rating, review_count

    except Exception as e:
        print(f"  ❌ Error during extraction: {e}")
        return "N/A", "N/A"

# ---------- Main hotel processing ----------
def process_hotel(hotel_name):
    print(f"\n🔍 Processing: {hotel_name}")

    ta_url = find_tripadvisor_page_via_google(hotel_name)
    if not ta_url:
        print("  ❌ No TripAdvisor page found in Google results.")
        return "N/A", "N/A"

    rating, reviews = extract_from_tripadvisor_page(ta_url)
    return rating, reviews

# ---------- Excel reading (unchanged) ----------
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
        return hotels
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
        return []

# ---------- Configuration ----------
EXCEL_FILE_PATH = r"C:/Users/Administrator/Desktop/RatingsProject/property_files/Shobhit_Property_List.xlsx"
OUTPUT_CSV_FILE = r"C:/Users/Administrator/Desktop/RatingsProject/Results/Shobhit_Property_List_tripadvisor_results.csv"
SHEET_NAME = 0
HOTEL_COLUMN_NAME = "Hotel Name"

output_dir = os.path.dirname(OUTPUT_CSV_FILE)
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir)

print("="*60)
print("TRIPADVISOR SCRAPER - Fixed Rating Extraction (before green dots)")
print("="*60)
print(f"\n📁 Input Excel: {EXCEL_FILE_PATH}")
print(f"📁 Output CSV: {OUTPUT_CSV_FILE}")
print(f"📋 Hotel column: '{HOTEL_COLUMN_NAME}'")
print("\n⚠️  Using Google to find TripAdvisor hotel pages, then extracting rating (e.g., 4.7) and review count.\n")

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
            "Rating (out of 5)": rating,
            "Review Count": reviews,
            "Platform": "TripAdvisor"
        })

        print(f"  📊 FINAL: {hotel} → Rating={rating}/5, Reviews={reviews}")

        # Save only the main CSV file (no extra timestamped or backup files)
        pd.DataFrame(results).to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')

        if i < len(hotels):
            delay = random.uniform(12, 18)
            print(f"  ⏳ Waiting {delay:.0f} seconds before next hotel...")
            time.sleep(delay)

    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    df_final = pd.DataFrame(results)
    ratings_found = sum(1 for r in results if r['Rating (out of 5)'] != 'N/A')
    reviews_found = sum(1 for r in results if r['Review Count'] != 'N/A')
    print(f"\n📊 Success: Ratings {ratings_found}/{len(results)} ({ratings_found/len(results)*100:.1f}%)")
    print(f"          Review counts {reviews_found}/{len(results)} ({reviews_found/len(results)*100:.1f}%)")

    print(f"\n✅ Done! Results saved to: {OUTPUT_CSV_FILE}")

except KeyboardInterrupt:
    print("\n⚠️ Interrupted – partial results are not saved (only the final CSV will contain all processed hotels).")
except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    driver.quit()
    print("👋 Browser closed")