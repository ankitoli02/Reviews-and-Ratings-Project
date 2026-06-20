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

# Setup Chrome
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

def extract_from_booking_search(hotel_name):
    """Extract rating and review count from Booking.com search results"""
    
    print(f"\n🔍 Searching Booking.com for: {hotel_name}")
    
    try:
        # Search Booking.com
        search_query = hotel_name.replace(' ', '+')
        url = f"https://www.booking.com/searchresults.html?ss={search_query}"
        
        driver.get(url)
        random_delay(5, 7)
        
        rating = "N/A"
        review_count = "N/A"
        
        try:
            # Wait for search results to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='property-card']"))
            )
            
            # Find all property cards
            property_cards = driver.find_elements(By.CSS_SELECTOR, "[data-testid='property-card']")
            
            if property_cards:
                # Check first few cards for matching hotel name
                for card in property_cards[:5]:  # Check first 5 results
                    try:
                        # Get hotel name from card
                        hotel_element = card.find_element(By.CSS_SELECTOR, "[data-testid='title']")
                        card_hotel_name = hotel_element.text.strip()
                        
                        # Check if hotel name matches (partial match)
                        if hotel_name.lower() in card_hotel_name.lower() or card_hotel_name.lower() in hotel_name.lower():
                            print(f"  ✅ Found matching hotel: {card_hotel_name}")
                            
                            # Extract rating
                            try:
                                rating_element = card.find_element(By.CSS_SELECTOR, "[data-testid='review-score']")
                                rating_text = rating_element.text
                                # Extract numeric rating (e.g., "8.5" from "8.5 Good")
                                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                                if rating_match:
                                    rating = rating_match.group(1)
                                    print(f"  ✅ Rating found: {rating}")
                            except:
                                pass
                            
                            # Extract review count
                            try:
                                # Method 1: Try to find review count in the review-score component
                                review_component = card.find_element(By.CSS_SELECTOR, "[data-testid='review-score']")
                                full_text = review_component.text
                                
                                # Look for patterns like "1,234 reviews" or "(1,234 reviews)"
                                count_patterns = [
                                    r'([\d,]+)\s*reviews?',
                                    r'\(([\d,]+)\s*reviews?\)',
                                    r'([\d,]+)\s*review',
                                    r'([\d,]+)\s*ratings?',
                                ]
                                
                                for pattern in count_patterns:
                                    match = re.search(pattern, full_text, re.IGNORECASE)
                                    if match:
                                        review_count = match.group(1).replace(',', '')
                                        print(f"  ✅ Review count found: {review_count}")
                                        break
                                
                                # If still not found, try finding via XPATH
                                if review_count == "N/A":
                                    try:
                                        review_elements = card.find_elements(By.XPATH, ".//div[contains(@class, 'review-count') or contains(@class, 'bui-review-score')]")
                                        for elem in review_elements:
                                            text = elem.text
                                            match = re.search(r'([\d,]+)', text)
                                            if match and int(match.group(1).replace(',', '')) > 10:  # Ignore small numbers
                                                review_count = match.group(1).replace(',', '')
                                                print(f"  ✅ Review count found (alternative): {review_count}")
                                                break
                                    except:
                                        pass
                                        
                            except Exception as e:
                                print(f"  ⚠️ Could not extract review count: {e}")
                            
                            break
                    except Exception as e:
                        continue
                        
        except Exception as e:
            print(f"  ⚠️ Could not find property cards: {e}")
        
        return rating, review_count
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return "N/A", "N/A"

# ===== DIRECT URL APPROACH - COMMENTED OUT (NOT WORKING) =====
# def extract_from_booking_direct(hotel_name):
#     """Try to go directly to Booking.com hotel page"""
#     
#     # Clean hotel name for URL
#     clean_name = hotel_name.lower().strip()
#     clean_name = re.sub(r'[^a-z0-9\s]', '', clean_name)
#     clean_name = re.sub(r'\s+', '-', clean_name)
#     
#     # Try multiple URL patterns
#     url_patterns = [
#         f"https://www.booking.com/hotel/{clean_name}.html",
#         f"https://www.booking.com/hotel/in/{clean_name}.html",
#     ]
#     
#     for url in url_patterns:
#         try:
#             print(f"  🔗 Trying: {url}")
#             driver.get(url)
#             random_delay(5, 7)
#             
#             # Check if we got a valid page (not error page)
#             page_source = driver.page_source
#             if "property not found" not in page_source.lower() and len(page_source) > 1000:
#                 
#                 rating = "N/A"
#                 review_count = "N/A"
#                 
#                 # Try to find rating and review count
#                 try:
#                     # Wait for review section to load
#                     WebDriverWait(driver, 10).until(
#                         EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='review-score-component']"))
#                     )
#                     
#                     # Get the entire review section text
#                     review_section = driver.find_element(By.CSS_SELECTOR, "[data-testid='review-score-component']")
#                     section_text = review_section.text
#                     
#                     # Extract rating
#                     rating_match = re.search(r'(\d+\.?\d*)', section_text)
#                     if rating_match:
#                         rating = rating_match.group(1)
#                         print(f"  ✅ Rating found: {rating}")
#                     
#                     # Extract review count
#                     count_patterns = [
#                         r'([\d,]+)\s*reviews?',
#                         r'([\d,]+)\s*Ratings?',
#                         r'based on\s+([\d,]+)',
#                         r'\(([\d,]+)\)',
#                     ]
#                     
#                     for pattern in count_patterns:
#                         match = re.search(pattern, section_text, re.IGNORECASE)
#                         if match:
#                             review_count = match.group(1).replace(',', '')
#                             print(f"  ✅ Review count found: {review_count}")
#                             break
#                     
#                     # Try alternative selectors if still not found
#                     if review_count == "N/A":
#                         try:
#                             review_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='review-count'], [class*='review_count']")
#                             for elem in review_elements:
#                                 text = elem.text
#                                 match = re.search(r'([\d,]+)', text)
#                                 if match and int(match.group(1).replace(',', '')) > 10:
#                                     review_count = match.group(1).replace(',', '')
#                                     print(f"  ✅ Review count found (alternative): {review_count}")
#                                     break
#                         except:
#                             pass
#                             
#                 except Exception as e:
#                     print(f"  ⚠️ Could not extract data from page: {e}")
#                 
#                 return rating, review_count
#                 
#         except Exception as e:
#             continue
#     
#     return "N/A", "N/A"

def extract_from_google_booking_snippet(hotel_name):
    """Extract Booking.com rating and review count from Google search results"""
    
    print(f"\n🔍 Searching Google for: booking.com {hotel_name}")
    
    try:
        # Search Google
        search_query = f"booking.com {hotel_name} rating"
        url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        
        driver.get(url)
        random_delay(3, 5)
        
        # Get the entire page text
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        rating = "N/A"
        review_count = "N/A"
        
        # ===== EXTRACT RATING =====
        rating_patterns = [
            r'Rating[:\s]*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*/\s*10',
            r'(\d+\.?\d*)\s*out of\s*10',
            r'(\d+\.?\d*)\s*★',
            r'(\d+\.?\d*)\s*star',
        ]
        
        for pattern in rating_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                rating = match.group(1)
                print(f"  ✅ Rating found: {rating}")
                break
        
        # ===== EXTRACT REVIEW COUNT =====
        count_patterns = [
            r'([\d,]+)\s*reviews?',
            r'([\d,]+)\s*Ratings?',
            r'([\d,]+)\s*review[s]?\s*\([^)]*\)',
            r'Based on\s+([\d,]+)\s+reviews',
        ]
        
        for pattern in count_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                review_count = match.group(1).replace(',', '')
                print(f"  ✅ Review count found: {review_count}")
                break
        
        # Try to click on Booking.com link for more accurate data
        try:
            booking_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Booking.com")
            
            for link in booking_links:
                try:
                    href = link.get_attribute("href")
                    if href and "booking.com" in href and "/hotel/" in href:
                        print(f"  🔗 Found Booking.com link, attempting to open...")
                        driver.execute_script("window.open(arguments[0], '_blank');", href)
                        random_delay(2, 3)
                        
                        # Switch to new tab
                        driver.switch_to.window(driver.window_handles[-1])
                        random_delay(5, 7)
                        
                        # Extract from Booking.com page
                        try:
                            review_section = driver.find_element(By.CSS_SELECTOR, "[data-testid='review-score-component']")
                            section_text = review_section.text
                            
                            # Extract rating
                            rating_match = re.search(r'(\d+\.?\d*)', section_text)
                            if rating_match:
                                rating = rating_match.group(1)
                            
                            # Extract review count
                            for pattern in count_patterns:
                                match = re.search(pattern, section_text, re.IGNORECASE)
                                if match:
                                    review_count = match.group(1).replace(',', '')
                                    break
                        except:
                            pass
                        
                        # Close tab and switch back
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        break
                        
                except Exception as e:
                    print(f"  ⚠️ Error with link: {e}")
                    continue
                    
        except Exception as e:
            print(f"  ⚠️ Could not open Booking.com link: {e}")
        
        return rating, review_count
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return "N/A", "N/A"

def read_hotels_from_excel(file_path, sheet_name=0, column_name='Hotel Name'):
    """
    Read hotel names from Excel file
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return []
        
        # Read Excel file
        if file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        elif file_path.endswith('.xls'):
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            print(f"❌ Unsupported file format. Please use .xlsx or .xls file")
            return []
        
        # Check if column exists
        if column_name not in df.columns:
            print(f"❌ Column '{column_name}' not found in the Excel file")
            print(f"Available columns: {list(df.columns)}")
            return []
        
        # Extract hotel names, drop empty values
        hotels = df[column_name].dropna().tolist()
        
        # Convert to string and strip whitespace
        hotels = [str(hotel).strip() for hotel in hotels]
        
        print(f"✅ Loaded {len(hotels)} hotels from '{file_path}'")
        print(f"📋 First 5 hotels: {hotels[:5]}{'...' if len(hotels) > 5 else ''}")
        
        return hotels
        
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return []

# ===== MAIN EXECUTION =====
# CONFIGURATION
EXCEL_FILE_PATH = r"C:/Users/Administrator/Desktop/RatingsProject/property_files/Shobhit_Property_List.xlsx"
OUTPUT_CSV_FILE = r"C:/Users/Administrator/Desktop/RatingsProject/Results/Shobhit_Property_List_booking_results.csv"
SHEET_NAME = 0
HOTEL_COLUMN_NAME = "Hotel Name"

# Create Results directory if it doesn't exist
output_dir = os.path.dirname(OUTPUT_CSV_FILE)
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"✅ Created output directory: {output_dir}")

print("="*60)
print("BOOKING.COM HOTEL DATA SCRAPER (DIRECT URL SKIPPED)")
print("="*60)
print(f"\n📁 Input Excel file: {EXCEL_FILE_PATH}")
print(f"📁 Output CSV file: {OUTPUT_CSV_FILE}")
print(f"📋 Hotel column name: '{HOTEL_COLUMN_NAME}'")

print("\n⚠️ NOTE: Direct URL approach is DISABLED (not working)")
print("   Using: Search results + Google fallback only\n")

# Read hotels from Excel file
hotels = read_hotels_from_excel(EXCEL_FILE_PATH, SHEET_NAME, HOTEL_COLUMN_NAME)

if not hotels:
    print("\n❌ No hotels found! Please check your Excel file.")
    driver.quit()
    exit()
else:
    print(f"\n🚀 Starting scraping for {len(hotels)} hotels...")
    
results = []

try:
    for i, hotel in enumerate(hotels, 1):
        print(f"\n{'='*60}")
        print(f"Progress: {i}/{len(hotels)} - {hotel}")
        print('='*60)
        
        # Try Strategy 1: Search on Booking.com
        rating, review_count = extract_from_booking_search(hotel)
        
        # Strategy 2: If not found, try Google search (Direct URL is SKIPPED)
        if rating == "N/A" and review_count == "N/A":
            print("  🔄 Trying Google search for Booking.com data...")
            rating, review_count = extract_from_google_booking_snippet(hotel)
        
        # Save result
        results.append({
            "Hotel Name": hotel,
            "Rating (out of 10)": rating,
            "Review Count": review_count,
            "Platform": "Booking.com"
        })
        
        print(f"  📊 FINAL: {hotel} → Rating={rating}/10, Reviews={review_count}")
        
        # Save to CSV after each hotel
        df = pd.DataFrame(results)
        df.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
        print(f"  💾 Saved to {OUTPUT_CSV_FILE}")
        
        # Random delay between hotels
        if i < len(hotels):
            delay = random.uniform(8, 12)
            print(f"  ⏳ Waiting {delay:.0f} seconds...")
            time.sleep(delay)
    
    # Final summary
    print("\n" + "="*60)
    print("FINAL RESULTS SUMMARY:")
    print("="*60)
    final_df = pd.DataFrame(results)
    
    # Calculate success rate
    ratings_found = sum(1 for r in results if r['Rating (out of 10)'] != 'N/A')
    reviews_found = sum(1 for r in results if r['Review Count'] != 'N/A')
    
    print(f"\n📊 SUCCESS RATE:")
    print(f"   Ratings found: {ratings_found}/{len(results)} ({ratings_found/len(results)*100:.1f}%)")
    print(f"   Review counts found: {reviews_found}/{len(results)} ({reviews_found/len(results)*100:.1f}%)")
    
    print("\n📋 DETAILED RESULTS:")
    print(final_df.to_string(index=False))
    
    # Save final results with timestamp
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    final_output_file = os.path.join(output_dir, f"booking_final_results_{timestamp}.csv")
    final_df.to_csv(final_output_file, index=False, encoding='utf-8-sig')
    
    excel_output_file = os.path.join(output_dir, f"booking_results_{timestamp}.xlsx")
    final_df.to_excel(excel_output_file, index=False)
    
    print(f"\n✅ Done! Results saved to:")
    print(f"   - {OUTPUT_CSV_FILE} (latest results)")
    print(f"   - {final_output_file} (dated backup)")
    print(f"   - {excel_output_file} (Excel format)")

except KeyboardInterrupt:
    print("\n⚠️ Interrupted! Saving partial results...")
    if results:
        partial_file = os.path.join(output_dir, "booking_partial_results.csv")
        pd.DataFrame(results).to_csv(partial_file, index=False, encoding='utf-8-sig')
        print(f"💾 Saved partial results to {partial_file}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    if results:
        partial_file = os.path.join(output_dir, "booking_partial_results.csv")
        pd.DataFrame(results).to_csv(partial_file, index=False, encoding='utf-8-sig')
        print(f"💾 Saved partial results to {partial_file}")

finally:
    driver.quit()
    print("👋 Browser closed")