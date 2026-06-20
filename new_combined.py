"""
Consolidated Hotel Ratings Scraper
====================================
Scrapes ratings and review counts for each hotel from:
  - Agoda        (Rating /10)
  - Booking.com  (Rating /10)
  - Goibibo      (Rating /5)
  - Google Maps  (Rating /5)
  - MakeMyTrip   (Rating /5)
  - TripAdvisor  (Rating /5)

Output: Single Excel file matching the Consolidated_Ratings.xlsx format
Columns: Hotel Name, Agoda_Rating, Agoda_Reviews, Booking.com_Rating,
         Booking.com_Reviews, Goibibo_Rating, Goibibo_Reviews,
         Google_Rating, Google_Reviews, MMT_Rating, MMT_Reviews,
         Tripadvisor_Rating, Tripadvisor_Reviews
"""

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

# ============================================================
# CONFIGURATION  ← Edit these paths before running
# ============================================================
EXCEL_FILE_PATH   = r"C:/Users/Administrator/Desktop/RatingsProject/property_files/EcoHotels.xlsx"
OUTPUT_EXCEL_FILE = r"C:/Users/Administrator/Desktop/RatingsProject/Results/Eco_Reviews_&_Ratings.xlsx"
SHEET_NAME        = 0            # 0 = first sheet
HOTEL_COLUMN_NAME = "Hotel Name"

# Delays (seconds) — increase if getting blocked
DELAY_BETWEEN_HOTELS   = (15, 22)   # pause between hotels
DELAY_BETWEEN_PLATFORMS = (8, 12)   # pause between platforms for same hotel
PAGE_LOAD_WAIT         = (4, 6)
GOOGLE_WAIT            = (3, 5)

# Platforms to scrape — set False to skip any
SCRAPE = {
    "agoda":      False,
    "booking":    False,
    "goibibo":    True,
    "google":     False,
    "mmt":        True,     # <-- NOW ENABLED
    "tripadvisor": False,
}
# ============================================================

# ---------- Chrome stealth setup ----------
def create_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--start-maximized")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    drv = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    drv.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return drv

def rnd(lo, hi):
    time.sleep(random.uniform(lo, hi))

def dismiss_cookie_popup(driver):
    """Try to click common cookie/popup buttons."""
    try:
        for btn_text in ["Accept", "Accept all", "Agree", "Got it", "OK", "Close"]:
            try:
                btn = driver.find_element(By.XPATH, f"//button[contains(text(), '{btn_text}')]")
                btn.click()
                time.sleep(1)
                break
            except:
                continue
    except:
        pass

# ============================================================
# AGODA
# ============================================================
def scrape_agoda(driver, hotel_name):
    """Returns (rating_str, review_count_str) for Agoda via Google → Agoda page."""
    print(f"    [Agoda] Searching...")
    try:
        query = f"agoda {hotel_name}"
        driver.get(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        rnd(*GOOGLE_WAIT)

        agoda_url = None
        for link in driver.find_elements(By.XPATH, "//a[contains(@href, 'agoda.com')]"):
            href = link.get_attribute("href")
            if href and "agoda.com" in href and "/hotel/" in href:
                agoda_url = href
                break

        if not agoda_url:
            print("    [Agoda] No hotel page found on Google.")
            return "N/A", "N/A"

        print(f"    [Agoda] Opening page...")
        driver.get(agoda_url)
        dismiss_cookie_popup(driver)
        rnd(5, 7)
        driver.execute_script("window.scrollTo(0, 600);")
        rnd(2, 3)

        page_html = driver.page_source
        page_text = driver.find_element(By.TAG_NAME, "body").text

        rating = "N/A"
        for selector in ["[data-selenium='review-score']", "[class*='ReviewScore']",
                         "[class*='review-score']", ".Review__score", "[itemprop='ratingValue']"]:
            try:
                elem = driver.find_element(By.CSS_SELECTOR, selector)
                m = re.search(r'(\d+\.?\d*)', elem.text)
                if m:
                    rating = m.group(1); break
            except:
                pass
        if rating == "N/A":
            for pat in [r'(\d+\.?\d*)\s*/\s*10', r'(\d+\.?\d*)\s*out of 10',
                        r'Rating:\s*(\d+\.?\d*)', r'Score:\s*(\d+\.?\d*)']:
                m = re.search(pat, page_html, re.IGNORECASE)
                if m:
                    rating = m.group(1); break

        review_count = "N/A"
        for pat in [r'([\d,]+)\s*reviews?', r'([\d,]+)\s*Ratings?',
                    r'([\d,]+)\s*Guest\s+reviews?', r'([\d,]+)\s*verified\s+reviews?']:
            m = re.search(pat, page_text, re.IGNORECASE)
            if m:
                review_count = m.group(1).replace(',', ''); break
        if review_count == "N/A":
            for pat in [r'([\d,]+)\s*reviews?', r'([\d,]+)\s*Ratings?']:
                m = re.search(pat, page_html, re.IGNORECASE)
                if m:
                    review_count = m.group(1).replace(',', ''); break

        print(f"    [Agoda] Rating={rating}, Reviews={review_count}")
        return rating, review_count

    except Exception as e:
        print(f"    [Agoda] Error: {e}")
        return "N/A", "N/A"


# ============================================================
# BOOKING.COM
# ============================================================
def scrape_booking(driver, hotel_name):
    """Returns (rating_str, review_count_str) for Booking.com."""
    print(f"    [Booking] Searching...")
    rating, review_count = "N/A", "N/A"

    # Strategy 1: Direct Booking.com search
    try:
        url = f"https://www.booking.com/searchresults.html?ss={hotel_name.replace(' ', '+')}"
        driver.get(url)
        dismiss_cookie_popup(driver)
        rnd(5, 7)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='property-card']"))
        )
        cards = driver.find_elements(By.CSS_SELECTOR, "[data-testid='property-card']")
        for card in cards[:5]:
            try:
                card_name = card.find_element(By.CSS_SELECTOR, "[data-testid='title']").text.strip()
                if (hotel_name.lower() in card_name.lower() or
                        card_name.lower() in hotel_name.lower()):
                    score_elem = card.find_element(By.CSS_SELECTOR, "[data-testid='review-score']")
                    score_text = score_elem.text
                    m = re.search(r'(\d+\.?\d*)', score_text)
                    if m:
                        rating = m.group(1)
                    for pat in [r'([\d,]+)\s*reviews?', r'([\d,]+)\s*Ratings?']:
                        m2 = re.search(pat, score_text, re.IGNORECASE)
                        if m2:
                            review_count = m2.group(1).replace(',', ''); break
                    break
            except:
                continue
    except Exception as e:
        print(f"    [Booking] Direct search error: {e}")

    # Strategy 2: Google fallback
    if rating == "N/A" and review_count == "N/A":
        try:
            query = f"booking.com {hotel_name} rating"
            driver.get(f"https://www.google.com/search?q={query.replace(' ', '+')}")
            rnd(*GOOGLE_WAIT)
            page_text = driver.find_element(By.TAG_NAME, "body").text

            for pat in [r'(\d+\.?\d*)\s*/\s*10', r'Rating[:\s]*(\d+\.?\d*)',
                        r'(\d+\.?\d*)\s*out of\s*10']:
                m = re.search(pat, page_text, re.IGNORECASE)
                if m:
                    rating = m.group(1); break
            for pat in [r'([\d,]+)\s*reviews?', r'([\d,]+)\s*Ratings?']:
                m = re.search(pat, page_text, re.IGNORECASE)
                if m:
                    review_count = m.group(1).replace(',', ''); break
        except Exception as e:
            print(f"    [Booking] Google fallback error: {e}")

    print(f"    [Booking] Rating={rating}, Reviews={review_count}")
    return rating, review_count


# ============================================================
# GOIBIBO (FIXED - Direct site search)
# ============================================================
def scrape_goibibo(driver, hotel_name):
    """Returns (rating_str, review_count_str) for Goibibo via direct hotel page."""
    print(f"    [Goibibo] Searching directly...")
    try:
        # Build a possible Goibibo hotel URL (slugify hotel name)
        slug = hotel_name.lower().replace(' ', '-')
        # Remove special characters
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        url = f"https://www.goibibo.com/hotels/{slug}/"
        
        driver.get(url)
        dismiss_cookie_popup(driver)
        
        # Wait for rating element to appear (various possible selectors)
        try:
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".avgRating, .rating__review, .Rating__Average, .hotel-detail-right"))
            )
        except:
            pass
        
        # Scroll to trigger lazy loading
        driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(3)
        
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Look for rating pattern like "4.2/5" or "4.2 ★"
        rating = "N/A"
        patterns = [r'(\d+\.?\d*)\s*/\s*5', r'(\d+\.?\d*)\s*★', r'Rating\s*:\s*(\d+\.?\d*)']
        for pat in patterns:
            m = re.search(pat, body_text, re.IGNORECASE)
            if m:
                rating = m.group(1)
                break
        
        # Look for review count
        review_count = "N/A"
        patterns_rev = [r'(\d{1,3}(?:,\d{3})*)\s*reviews?', r'(\d+)\s*Ratings?']
        for pat in patterns_rev:
            m = re.search(pat, body_text, re.IGNORECASE)
            if m:
                review_count = m.group(1).replace(',', '')
                break
        
        # If still no data, fallback to Google snippet (original method)
        if rating == "N/A" or review_count == "N/A":
            print("    [Goibibo] Direct failed, fallback to Google snippet...")
            query = f"goibibo {hotel_name} rating"
            driver.get(f"https://www.google.com/search?q={query.replace(' ', '+')}")
            rnd(*GOOGLE_WAIT)
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            if rating == "N/A":
                for pat in [r'Rating[:\s]*(\d+\.?\d*)', r'(\d+\.?\d*)\s*/\s*5',
                            r'(\d+\.?\d*)\s*out of\s*5', r'(\d+\.?\d*)\s*star']:
                    m = re.search(pat, page_text, re.IGNORECASE)
                    if m:
                        rating = m.group(1); break
            if review_count == "N/A":
                for pat in [r'([\d,]+)\s*reviews?', r'([\d,]+)\s*Ratings?', r'([\d,]+)\s*votes?']:
                    m = re.search(pat, page_text, re.IGNORECASE)
                    if m:
                        review_count = m.group(1).replace(',', ''); break
        
        print(f"    [Goibibo] Rating={rating}, Reviews={review_count}")
        return rating, review_count
        
    except Exception as e:
        print(f"    [Goibibo] Error: {e}")
        return "N/A", "N/A"


# ============================================================
# GOOGLE MAPS
# ============================================================
def scrape_google(driver, hotel_name):
    """Returns (rating_str, review_count_str) for Google Maps."""
    print(f"    [Google] Searching...")
    try:
        query = f"{hotel_name} hotel"
        driver.get(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        rnd(*PAGE_LOAD_WAIT)
        driver.execute_script("window.scrollTo(0, 400);")
        rnd(1, 2)

        rating = "N/A"
        # Method 1: aria-label
        for elem in driver.find_elements(By.XPATH, "//*[@aria-label]"):
            aria = elem.get_attribute("aria-label").lower()
            m = re.search(r'rated\s*(\d+\.?\d*)\s*out\s*of\s*5', aria)
            if m:
                rating = m.group(1); break
            m = re.search(r'(\d+\.?\d*)\s*stars?', aria)
            if m:
                rating = m.group(1); break

        # Method 2: known CSS classes
        if rating == "N/A":
            for cls in ["Aq14fc", "fzvQIb", "BHMmbe", "ZkP5Je"]:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, f".{cls}")
                    m = re.search(r'(\d+\.?\d*)', elem.text)
                    if m:
                        rating = m.group(1); break
                except:
                    continue

        # Method 3: regex on body
        if rating == "N/A":
            body = driver.find_element(By.TAG_NAME, "body").text
            for pat in [r'(\d+\.?\d*)\s*out of 5', r'(\d+\.?\d*)\s*·',
                        r'(\d+\.?\d*)\s*stars?', r'Rating:\s*(\d+\.?\d*)']:
                m = re.search(pat, body, re.IGNORECASE)
                if m:
                    rating = m.group(1); break

        review_count = "N/A"
        body = driver.find_element(By.TAG_NAME, "body").text
        for pat in [r'([\d,]+)\s*Google\s*reviews?', r'([\d,]+)\s*reviews?',
                    r'([\d.]+[Kk])\s*reviews?']:
            m = re.search(pat, body, re.IGNORECASE)
            if m:
                raw = m.group(1)
                if 'K' in raw.upper():
                    review_count = str(int(float(raw.replace('K','').replace('k','')) * 1000))
                else:
                    review_count = raw.replace(',', '')
                break

        print(f"    [Google] Rating={rating}, Reviews={review_count}")
        return rating, review_count

    except Exception as e:
        print(f"    [Google] Error: {e}")
        return "N/A", "N/A"


# ============================================================
# MAKEMYTRIP (MMT) - FIXED with direct search
# ============================================================
def scrape_mmt(driver, hotel_name):
    """Returns (rating_str, review_count_str) for MakeMyTrip."""
    print(f"    [MMT] Searching...")
    try:
        # Direct MMT search
        search_url = f"https://www.makemytrip.com/hotels/{hotel_name.replace(' ', '-')}-hotels.html"
        driver.get(search_url)
        dismiss_cookie_popup(driver)
        rnd(5, 7)
        
        # Try to locate rating element
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ratingArea, .ratingText, .ratingScore"))
            )
        except:
            pass
        
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        rating = "N/A"
        patterns = [r'(\d+\.?\d*)\s*/\s*5', r'(\d+\.?\d*)\s*★', r'Rating\s*:\s*(\d+\.?\d*)']
        for pat in patterns:
            m = re.search(pat, body_text, re.IGNORECASE)
            if m:
                rating = m.group(1)
                break
        
        review_count = "N/A"
        patterns_rev = [r'([\d,]+)\s*reviews?', r'([\d,]+)\s*Ratings?']
        for pat in patterns_rev:
            m = re.search(pat, body_text, re.IGNORECASE)
            if m:
                review_count = m.group(1).replace(',', '')
                break
        
        # Fallback: Google snippet if direct fails
        if rating == "N/A" or review_count == "N/A":
            print("    [MMT] Direct failed, fallback to Google snippet...")
            query = f"site:makemytrip.com {hotel_name} rating"
            driver.get(f"https://www.google.com/search?q={query.replace(' ', '+')}")
            rnd(*GOOGLE_WAIT)
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            if rating == "N/A":
                for pat in [r'(\d+\.?\d*)\s*[★☆]', r'(\d+\.?\d*)\s*/\s*5',
                            r'Rating[:\s]*(\d+\.?\d*)', r'(\d+\.?\d*)\s*out of 5']:
                    m = re.search(pat, page_text, re.IGNORECASE)
                    if m:
                        rating = m.group(1); break
            if review_count == "N/A":
                for pat in [r'([\d,]+)\s+reviews?', r'([\d,]+)\s+Google\s+reviews?',
                            r'\(([\d,]+)\)', r'([\d,]+)\s+Ratings?']:
                    m = re.search(pat, page_text, re.IGNORECASE)
                    if m:
                        review_count = m.group(1).replace(',', ''); break
        
        print(f"    [MMT] Rating={rating}, Reviews={review_count}")
        return rating, review_count

    except Exception as e:
        print(f"    [MMT] Error: {e}")
        return "N/A", "N/A"


# ============================================================
# TRIPADVISOR
# ============================================================
def scrape_tripadvisor(driver, hotel_name):
    """Returns (rating_str, review_count_str) for TripAdvisor via Google → TA page."""
    print(f"    [TripAdvisor] Searching...")
    try:
        query = f"tripadvisor {hotel_name}"
        driver.get(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        rnd(*GOOGLE_WAIT)

        ta_url = None
        for link in driver.find_elements(By.XPATH, "//a[contains(@href, 'tripadvisor.com')]"):
            href = link.get_attribute("href")
            if href and "tripadvisor.com" in href and "/Hotel_Review-" in href:
                ta_url = href; break

        if not ta_url:
            print("    [TripAdvisor] No hotel page found.")
            return "N/A", "N/A"

        driver.get(ta_url)
        dismiss_cookie_popup(driver)
        rnd(6, 8)
        driver.execute_script("window.scrollTo(0, 1000);")
        rnd(2, 3)

        page_source = driver.page_source
        page_text = driver.find_element(By.TAG_NAME, "body").text

        rating = "N/A"
        rating_patterns = [
            r'(\d+(?:\.\d+)?)\s*\(\d+[\d,]*\s*reviews?\)',
            r'aria-label="[^"]*(\d+(?:\.\d+)?)\s*out of 5[^"]*"',
            r'bubble_rating\D*(\d+(?:\.\d+)?)',
        ]
        for pat in rating_patterns:
            for text in [page_text, page_source]:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    rating = m.group(1); break
            if rating != "N/A":
                break

        if rating == "N/A":
            for div in driver.find_elements(
                    By.XPATH, "//*[contains(text(), '(') and contains(text(), 'reviews')]"):
                m = re.search(r'(\d+(?:\.\d+)?)\s*\(', div.text)
                if m:
                    rating = m.group(1); break

        review_count = "N/A"
        for pat in [r'([\d,]+)\s*reviews?', r'\(([\d,]+)\s*reviews?\)',
                    r'([\d,]+)\s*ratings?']:
            for text in [page_text, page_source]:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    review_count = m.group(1).replace(',', ''); break
            if review_count != "N/A":
                break

        print(f"    [TripAdvisor] Rating={rating}, Reviews={review_count}")
        return rating, review_count

    except Exception as e:
        print(f"    [TripAdvisor] Error: {e}")
        return "N/A", "N/A"


# ============================================================
# EXCEL HELPERS
# ============================================================
def read_hotels(file_path, sheet_name, column_name):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}"); return []
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        if column_name not in df.columns:
            print(f"❌ Column '{column_name}' not found. Available: {list(df.columns)}")
            return []
        hotels = [str(h).strip() for h in df[column_name].dropna().tolist()]
        print(f"✅ Loaded {len(hotels)} hotels")
        return hotels
    except Exception as e:
        print(f"❌ Error reading Excel: {e}"); return []


def save_to_excel(results, output_path):
    """Save results list to the consolidated Excel format."""
    df = pd.DataFrame(results, columns=[
        "Hotel Name",
        "Agoda_Rating", "Agoda_Reviews",
        "Booking.com_Rating", "Booking.com_Reviews",
        "Goibibo_Rating", "Goibibo_Reviews",
        "Google_Rating", "Google_Reviews",
        "MMT_Rating", "MMT_Reviews",
        "Tripadvisor_Rating", "Tripadvisor_Reviews",
    ])
    df.to_excel(output_path, sheet_name="Consolidated Ratings", index=False)
    print(f"  💾 Saved → {output_path}")


# ============================================================
# MAIN
# ============================================================
def main():
    os.makedirs(os.path.dirname(OUTPUT_EXCEL_FILE), exist_ok=True)

    hotels = read_hotels(EXCEL_FILE_PATH, SHEET_NAME, HOTEL_COLUMN_NAME)
    if not hotels:
        print("❌ No hotels found. Exiting.")
        return

    driver = create_driver()
    results = []

    print("\n" + "="*65)
    print("  CONSOLIDATED HOTEL RATINGS SCRAPER")
    print("="*65)
    print(f"  Hotels  : {len(hotels)}")
    print(f"  Platforms: {', '.join(k for k, v in SCRAPE.items() if v)}")
    print(f"  Output  : {OUTPUT_EXCEL_FILE}")
    print("="*65 + "\n")

    try:
        for i, hotel in enumerate(hotels, 1):
            print(f"\n{'='*65}")
            print(f"  [{i}/{len(hotels)}]  {hotel}")
            print(f"{'='*65}")

            row = {"Hotel Name": hotel}

            # --- Agoda ---
            if SCRAPE["agoda"]:
                r, c = scrape_agoda(driver, hotel)
                rnd(*DELAY_BETWEEN_PLATFORMS)
            else:
                r, c = "N/A", "N/A"
            row["Agoda_Rating"] = r; row["Agoda_Reviews"] = c

            # --- Booking.com ---
            if SCRAPE["booking"]:
                r, c = scrape_booking(driver, hotel)
                rnd(*DELAY_BETWEEN_PLATFORMS)
            else:
                r, c = "N/A", "N/A"
            row["Booking.com_Rating"] = r; row["Booking.com_Reviews"] = c

            # --- Goibibo ---
            if SCRAPE["goibibo"]:
                r, c = scrape_goibibo(driver, hotel)
                rnd(*DELAY_BETWEEN_PLATFORMS)
            else:
                r, c = "N/A", "N/A"
            row["Goibibo_Rating"] = r; row["Goibibo_Reviews"] = c

            # --- Google ---
            if SCRAPE["google"]:
                r, c = scrape_google(driver, hotel)
                rnd(*DELAY_BETWEEN_PLATFORMS)
            else:
                r, c = "N/A", "N/A"
            row["Google_Rating"] = r; row["Google_Reviews"] = c

            # --- MMT ---
            if SCRAPE["mmt"]:
                r, c = scrape_mmt(driver, hotel)
                rnd(*DELAY_BETWEEN_PLATFORMS)
            else:
                r, c = "N/A", "N/A"
            row["MMT_Rating"] = r; row["MMT_Reviews"] = c

            # --- TripAdvisor ---
            if SCRAPE["tripadvisor"]:
                r, c = scrape_tripadvisor(driver, hotel)
            else:
                r, c = "N/A", "N/A"
            row["Tripadvisor_Rating"] = r; row["Tripadvisor_Reviews"] = c

            results.append(row)

            print(f"\n  ✅ Summary for '{hotel}':")
            print(f"     Agoda       : {row['Agoda_Rating']} | {row['Agoda_Reviews']} reviews")
            print(f"     Booking.com : {row['Booking.com_Rating']} | {row['Booking.com_Reviews']} reviews")
            print(f"     Goibibo     : {row['Goibibo_Rating']} | {row['Goibibo_Reviews']} reviews")
            print(f"     Google      : {row['Google_Rating']} | {row['Google_Reviews']} reviews")
            print(f"     MMT         : {row['MMT_Rating']} | {row['MMT_Reviews']} reviews")
            print(f"     TripAdvisor : {row['Tripadvisor_Rating']} | {row['Tripadvisor_Reviews']} reviews")

            # Incremental save after every hotel
            save_to_excel(results, OUTPUT_EXCEL_FILE)

            if i < len(hotels):
                delay = random.uniform(*DELAY_BETWEEN_HOTELS)
                print(f"\n  ⏳ Waiting {delay:.0f}s before next hotel...")
                time.sleep(delay)

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted — saving partial results...")
        if results:
            save_to_excel(results, OUTPUT_EXCEL_FILE)
            print("   Partial results saved.")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if results:
            save_to_excel(results, OUTPUT_EXCEL_FILE)
            print("   Results saved up to error.")

    finally:
        driver.quit()
        print("\n👋 Browser closed.")

    # Final summary
    total = len(results)
    if total:
        print("\n" + "="*65)
        print("  FINAL SUMMARY")
        print("="*65)
        for platform, col in [("Agoda","Agoda_Rating"), ("Booking.com","Booking.com_Rating"),
                               ("Goibibo","Goibibo_Rating"), ("Google","Google_Rating"),
                               ("MMT","MMT_Rating"), ("TripAdvisor","Tripadvisor_Rating")]:
            found = sum(1 for r in results if r.get(col, "N/A") != "N/A")
            print(f"  {platform:<14}: {found}/{total} ({found/total*100:.0f}%) ratings found")
        print(f"\n  📁 Output: {OUTPUT_EXCEL_FILE}")


if __name__ == "__main__":
    main()