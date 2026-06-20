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

def extract_from_google_snippet(hotel_name):
    """Extract rating and review count from Google search results"""
    
    print(f"\n🔍 Searching Google for: goibibo {hotel_name}")
    
    try:
        # Search Google
        search_query = f"goibibo {hotel_name} rating"
        url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        
        driver.get(url)
        random_delay(3, 5)
        
        # Get the entire page text
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        rating = "N/A"
        review_count = "N/A"
        
        # ===== EXTRACT RATING =====
        # Look for rating patterns near Goibibo
        rating_patterns = [
            r'Rating[:\s]*(\d+\.?\d*)',  # Rating: 4.2
            r'(\d+\.?\d*)\s*/\s*5',  # 4.2/5
            r'(\d+\.?\d*)\s*out of\s*5',  # 4.2 out of 5
            r'(\d+\.?\d*)\s*star',  # 4.2 star
        ]
        
        for pattern in rating_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                rating = match.group(1)
                print(f"  ✅ Rating found: {rating}")
                break
        
        # ===== EXTRACT REVIEW COUNT =====
        count_patterns = [
            r'([\d,]+)\s*reviews?',  # 1,234 reviews
            r'([\d,]+)\s*Ratings?',  # 1,234 Ratings
            r'([\d,]+)\s*votes?',  # 1,234 votes
        ]
        
        for pattern in count_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                review_count = match.group(1).replace(',', '')
                print(f"  ✅ Review count found: {review_count}")
                break
        
        # ===== TRY TO CLICK AND OPEN GOIBIBO LINK =====
        try:
            # Find Goibibo links
            goibibo_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "goibibo")
            
            for link in goibibo_links:
                try:
                    href = link.get_attribute("href")
                    if href and "goibibo.com" in href:
                        print(f"  🔗 Found Goibibo link, attempting to open...")
                        driver.execute_script("window.open(arguments[0], '_blank');", href)
                        random_delay(2, 3)
                        
                        # Switch to new tab
                        driver.switch_to.window(driver.window_handles[-1])
                        random_delay(4, 6)
                        
                        # Extract more specific data from Goibibo page
                        page_text_goibibo = driver.find_element(By.TAG_NAME, "body").text
                        
                        # Try to find more accurate data
                        for pattern in rating_patterns:
                            match = re.search(pattern, page_text_goibibo, re.IGNORECASE)
                            if match:
                                rating = match.group(1)
                                break
                        
                        for pattern in count_patterns:
                            match = re.search(pattern, page_text_goibibo, re.IGNORECASE)
                            if match:
                                review_count = match.group(1).replace(',', '')
                                break
                        
                        # Close tab and switch back
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        break
                        
                except Exception as e:
                    print(f"  ⚠️ Error with link: {e}")
                    continue
                    
        except Exception as e:
            print(f"  ⚠️ Could not open Goibibo link: {e}")
        
        return rating, review_count
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return "N/A", "N/A"

def try_direct_url_approach(hotel_name):
    """Try to construct Goibibo URL directly and extract data"""
    
    # Clean hotel name for URL
    clean_name = hotel_name.lower().strip()
    clean_name = re.sub(r'[^a-z0-9\s]', '', clean_name)
    clean_name = re.sub(r'\s+', '-', clean_name)
    
    # Try multiple URL patterns
    url_patterns = [
        f"https://www.goibibo.com/hotels/{clean_name}-hotel/",
        f"https://www.goibibo.com/hotels/{clean_name}/",
    ]
    
    for url in url_patterns:
        try:
            print(f"  🔗 Trying: {url}")
            driver.get(url)
            random_delay(4, 6)
            
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Check if we got a valid page (not 404)
            if len(page_text) > 500:  # Arbitrary length check
                rating = "N/A"
                review_count = "N/A"
                
                # Extract rating
                for pattern in [r'(\d+\.?\d*)\s*/\s*5', r'Rating[:\s]*(\d+\.?\d*)']:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        rating = match.group(1)
                        break
                
                # Extract review count
                for pattern in [r'([\d,]+)\s*reviews?', r'([\d,]+)\s*Ratings?']:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        review_count = match.group(1).replace(',', '')
                        break
                
                return rating, review_count
                
        except:
            continue
    
    return "N/A", "N/A"

def read_hotels_from_excel(file_path, sheet_name=0, column_name='Hotel Name'):
    """
    Read hotel names from Excel file
    
    Parameters:
    - file_path: Path to the Excel file
    - sheet_name: Sheet name or index (default: 0 for first sheet)
    - column_name: Name of the column containing hotel names (default: 'Hotel Name')
    
    Returns:
    - List of hotel names
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
# CONFIGURATION - Excel file path is set here
EXCEL_FILE_PATH = r"C:/Users/Administrator/Desktop/RatingsProject/property_files/Shobhit_Property_List.xlsx"  # Your Excel file path
SHEET_NAME = 0  # Sheet name or index (0 for first sheet)
HOTEL_COLUMN_NAME = "Hotel Name"  # Column name containing hotel names
OUTPUT_CSV_FILE = "C:/Users/Administrator/Desktop/RatingsProject/Results/Shobhit_Property_List_goibibo_results.csv"  # Output CSV file name

print("="*60)
print("GOIBIBO HOTEL DATA SCRAPER")
print("="*60)
print(f"\n📁 Excel file path: {EXCEL_FILE_PATH}")
print(f"📋 Hotel column name: '{HOTEL_COLUMN_NAME}'")

# Read hotels from Excel file
hotels = read_hotels_from_excel(EXCEL_FILE_PATH, SHEET_NAME, HOTEL_COLUMN_NAME)

if not hotels:
    print("\n❌ No hotels found! Please check your Excel file.")
    print("\nPlease ensure:")
    print("1. The Excel file exists at the specified path")
    print("2. The file has a column named 'Hotel Name'")
    print("3. The column contains hotel names")
    print(f"\nFile path: {EXCEL_FILE_PATH}")
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
        
        # Strategy 1: Extract from Google snippet
        rating, review_count = extract_from_google_snippet(hotel)
        
        # Strategy 2: If N/A, try direct URL
        if rating == "N/A" and review_count == "N/A":
            print("  🔄 Trying direct URL approach...")
            rating, review_count = try_direct_url_approach(hotel)
        
        # Save result
        results.append({
            "Hotel Name": hotel,
            "Rating": rating,
            "Review Count": review_count
        })
        
        print(f"  📊 {hotel}: Rating={rating}, Review Count={review_count}")
        
        # Save to CSV after each hotel
        df = pd.DataFrame(results)
        df.to_csv(OUTPUT_CSV_FILE, index=False)
        print(f"  💾 Saved to {OUTPUT_CSV_FILE}")
        
        # Random delay between hotels
        if i < len(hotels):
            delay = random.uniform(10, 15)
            print(f"  ⏳ Waiting {delay:.0f} seconds...")
            time.sleep(delay)
    
    print("\n" + "="*60)
    print("FINAL RESULTS:")
    print("="*60)
    final_df = pd.DataFrame(results)
    print(final_df.to_string(index=False))
    
    # Save final results with timestamp
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    final_output_file = f"goibibo_final_results_{timestamp}.csv"
    final_df.to_csv(final_output_file, index=False)
    print(f"\n✅ Done! Results saved to:")
    print(f"   - {OUTPUT_CSV_FILE} (latest results)")
    print(f"   - {final_output_file} (dated backup)")
    
    # Also save as Excel for easy viewing
    excel_output_file = f"goibibo_results_{timestamp}.xlsx"
    final_df.to_excel(excel_output_file, index=False)
    print(f"   - {excel_output_file} (Excel format)")

except KeyboardInterrupt:
    print("\n⚠️ Interrupted! Saving partial results...")
    if results:
        pd.DataFrame(results).to_csv("goibibo_partial_results.csv", index=False)
        pd.DataFrame(results).to_excel("goibibo_partial_results.xlsx", index=False)
        print("💾 Saved partial results to 'goibibo_partial_results.csv' and 'goibibo_partial_results.xlsx'")

except Exception as e:
    print(f"\n❌ Error: {e}")
    if results:
        pd.DataFrame(results).to_csv("goibibo_partial_results.csv", index=False)
        pd.DataFrame(results).to_excel("goibibo_partial_results.xlsx", index=False)
        print("💾 Saved partial results to 'goibibo_partial_results.csv' and 'goibibo_partial_results.xlsx'")

finally:
    driver.quit()
    print("👋 Browser closed")