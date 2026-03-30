# import os
# import time
# import shutil

# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import Select, WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.options import Options
# from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

# if not os.path.exists(DOWNLOAD_DIR):
#     os.makedirs(DOWNLOAD_DIR)


# def setup_driver():
#     chrome_options = Options()
#     chrome_options.add_argument("--headless=new")
#     chrome_options.add_argument("--disable-gpu")
#     chrome_options.add_argument("--no-sandbox")
#     chrome_options.add_argument("--window-size=1920,1080")
#     chrome_options.add_argument("--disable-dev-shm-usage")
#     chrome_options.add_experimental_option("prefs", {
#         "download.default_directory": DOWNLOAD_DIR,
#         "download.prompt_for_download": False,
#         "download.directory_upgrade": True,
#     })
#     driver = webdriver.Chrome(options=chrome_options)
#     return driver


# def safe_click(driver, element, retries=3):
#     for attempt in range(retries):
#         try:
#             driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
#             time.sleep(0.3)
#             element.click()
#             return True
#         except ElementClickInterceptedException:
#             try:
#                 driver.execute_script("arguments[0].click();", element)
#                 return True
#             except Exception:
#                 if attempt == retries - 1:
#                     raise
#                 time.sleep(1)
#         except Exception:
#             if attempt == retries - 1:
#                 raise
#             time.sleep(1)
#     return False


# def safe_rename(src, dst):
#     if os.path.exists(dst):
#         os.remove(dst)
#     shutil.move(src, dst)


# def _navigate_to_form(driver, is_import):
#     """
#     Open the site, click Import/Export, select Country-wise all Commodities.
#     Mirrors exactly what the working manual script does.
#     """
#     wait = WebDriverWait(driver, 20)
#     driver.get("https://tradestat.commerce.gov.in/eidb/commodity_wise_export")
#     time.sleep(2)

#     # Click Export (index 0) or Import (index 1) — same as working script
#     links = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.mt-2")))
#     driver.execute_script("arguments[0].click();", links[1 if is_import else 0])
#     time.sleep(1)

#     # Wait for dropdown button
#     wait.until(EC.presence_of_element_located((By.ID, "dropdownMenuButton")))

#     # Open dropdown
#     dropdown_btn = wait.until(EC.element_to_be_clickable((By.ID, "dropdownMenuButton")))
#     driver.execute_script("arguments[0].click();", dropdown_btn)
#     time.sleep(1)

#     # Select "Country-wise all Commodities"
#     options = wait.until(EC.presence_of_all_elements_located(
#         (By.CSS_SELECTOR, ".dropdown-menu.show a")
#     ))
#     for opt in options:
#         if "Country-wise all Commodities" in opt.text:
#             driver.execute_script("arguments[0].click();", opt)
#             break

#     time.sleep(2)
#     return wait


# def get_matching_countries(driver, search_text, is_import=False):
#     """
#     Return list of country names from dropdown that contain search_text.
#     Always uses Export tab for consistency (country list is same).
#     """
#     try:
#         wait = _navigate_to_form(driver, is_import=False)

#         # Always use export dropdown for country search
#         dropdown_id = "EidbCntcwace"
#         select_element = wait.until(EC.presence_of_element_located((By.ID, dropdown_id)))
#         select = Select(select_element)

#         search_lower = search_text.lower().strip()
#         matches = []
#         for option in select.options:
#             name = option.text.strip()
#             if name and search_lower in name.lower():
#                 matches.append(name)

#         return matches

#     except Exception as e:
#         print(f"Error in get_matching_countries: {e}")
#         return []


# def run_scraper(data_type, country, user_year):
#     """
#     Scrape trade data and return path to downloaded file.

#     user_year: the year user typed (e.g. "2025")
#                → site shows "2024-2025", we match by checking if user_year is IN option text

#     country: exact name from dropdown (e.g. "SAUDI ARAB")
#     """
#     driver = None
#     try:
#         driver = setup_driver()
#         is_import = data_type.lower() == "import"

#         wait = _navigate_to_form(driver, is_import)

#         # IDs based on type
#         year_id      = "EidbYearcwaci"    if is_import else "EidbYearcwace"
#         country_id   = "EidbCntcwaci"     if is_import else "EidbCntcwace"
#         currency_id  = "EidbReportcwaci"  if is_import else "EidbReportcwace"
#         commodity_id = "EidbComLevelcwaci" if is_import else "EidbComLevelcwace"

#         # ── SELECT YEAR ───────────────────────────────────────────────────
#         # Site shows "2024-2025" → match whichever option contains user_year
#         wait.until(EC.presence_of_element_located((By.ID, year_id)))
#         year_dropdown = Select(driver.find_element(By.ID, year_id))

#         year_selected = False
#         for opt in year_dropdown.options:
#             if user_year in opt.text:
#                 opt.click()
#                 year_selected = True
#                 print(f"✅ Year selected: {opt.text}")
#                 break

#         if not year_selected:
#             available = [o.text for o in year_dropdown.options]
#             raise Exception(f"Year '{user_year}' not found in dropdown. Available: {available}")

#         time.sleep(0.5)

#         # ── WAIT FOR COUNTRY DROPDOWN TO LOAD ────────────────────────────
#         wait.until(lambda d: len(Select(d.find_element(By.ID, country_id)).options) > 1)

#         # ── SELECT COUNTRY ────────────────────────────────────────────────
#         # Build list of (value, name) same as working script
#         country_element = driver.find_element(By.ID, country_id)
#         country_select = Select(country_element)

#         matched_value = None
#         matched_name = None
#         country_upper = country.upper().strip()

#         for opt in country_select.options:
#             name = opt.text.strip()
#             value = opt.get_attribute("value")
#             if value and name.upper() == country_upper:
#                 matched_value = value
#                 matched_name = name
#                 break

#         # Fallback: partial match
#         if not matched_value:
#             for opt in country_select.options:
#                 name = opt.text.strip()
#                 value = opt.get_attribute("value")
#                 if value and country_upper in name.upper():
#                     matched_value = value
#                     matched_name = name
#                     break

#         if not matched_value:
#             raise Exception(f"Country '{country}' not found in dropdown")

#         Select(driver.find_element(By.ID, country_id)).select_by_value(matched_value)
#         print(f"✅ Country selected: {matched_name}")
#         time.sleep(0.5)

#         # ── SELECT CURRENCY (USD) ─────────────────────────────────────────
#         Select(driver.find_element(By.ID, currency_id)).select_by_value("2")
#         time.sleep(0.3)

#         # ── SELECT COMMODITY (8 digit) ────────────────────────────────────
#         Select(driver.find_element(By.ID, commodity_id)).select_by_value("8")
#         time.sleep(0.3)

#         # ── SUBMIT ────────────────────────────────────────────────────────
#         # Use buttons[1] same as working script
#         buttons = driver.find_elements(By.TAG_NAME, "button")
#         driver.execute_script("arguments[0].click();", buttons[1])
#         print("⏳ Loading data...")

#         # ── WAIT FOR RESULT ───────────────────────────────────────────────
#         wait.until(
#             EC.any_of(
#                 EC.presence_of_element_located((By.CSS_SELECTOR, ".buttons-excel")),
#                 EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'No data')]")),
#                 EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'no record')]")),
#             )
#         )
#         time.sleep(3)

#         # Check if no data
#         if "No data" in driver.page_source or "no record" in driver.page_source.lower():
#             raise Exception(f"No data available for {country} {data_type} {user_year}")

#         # ── CLICK EXCEL DOWNLOAD ──────────────────────────────────────────
#         # Use buttons[2] same as working script
#         before_files = set(os.listdir(DOWNLOAD_DIR))
#         buttons = driver.find_elements(By.TAG_NAME, "button")
#         driver.execute_script("arguments[0].click();", buttons[2])
#         print("📥 Download started...")

#         # ── WAIT FOR FILE ─────────────────────────────────────────────────
#         timeout = 30
#         start = time.time()
#         new_file = None

#         while time.time() - start < timeout:
#             after_files = set(os.listdir(DOWNLOAD_DIR))
#             diff = after_files - before_files
#             if diff:
#                 candidate = diff.pop()
#                 if not candidate.endswith(".crdownload"):
#                     new_file = candidate
#                     break
#             time.sleep(1)

#         if not new_file:
#             raise Exception("File download timed out")

#         # ── RENAME FILE ───────────────────────────────────────────────────
#         old_path = os.path.join(DOWNLOAD_DIR, new_file)
#         safe_name = (matched_name or country).replace(" ", "_")
#         file_name = f"{data_type.capitalize()}-{safe_name}-{user_year}.xlsx"
#         new_path = os.path.join(DOWNLOAD_DIR, file_name)
#         safe_rename(old_path, new_path)

#         print(f"✅ File ready: {new_path}")
#         return new_path

#     except Exception as e:
#         print(f"Error in run_scraper: {e}")
#         raise
#     finally:
#         if driver:
#             try:
#                 driver.quit()
#             except Exception:
#                 pass


























import os
import time
import shutil

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)


def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--single-process")          # critical for Render
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
    })
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(60)
    return driver


def safe_click(driver, element, retries=3):
    for attempt in range(retries):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.3)
            element.click()
            return True
        except ElementClickInterceptedException:
            try:
                driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                if attempt == retries - 1:
                    raise
                time.sleep(1)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1)
    return False


def safe_rename(src, dst):
    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(src, dst)


def _navigate_to_form(driver, is_import):
    wait = WebDriverWait(driver, 20)
    driver.get("https://tradestat.commerce.gov.in/eidb/commodity_wise_export")
    time.sleep(2)

    links = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.mt-2")))
    driver.execute_script("arguments[0].click();", links[1 if is_import else 0])
    time.sleep(1)

    wait.until(EC.presence_of_element_located((By.ID, "dropdownMenuButton")))
    dropdown_btn = wait.until(EC.element_to_be_clickable((By.ID, "dropdownMenuButton")))
    driver.execute_script("arguments[0].click();", dropdown_btn)
    time.sleep(1)

    options = wait.until(EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, ".dropdown-menu.show a")
    ))
    for opt in options:
        if "Country-wise all Commodities" in opt.text:
            driver.execute_script("arguments[0].click();", opt)
            break

    time.sleep(2)
    return wait


def get_matching_countries(driver, search_text, is_import=False):
    try:
        wait = _navigate_to_form(driver, is_import=False)
        dropdown_id = "EidbCntcwace"
        select_element = wait.until(EC.presence_of_element_located((By.ID, dropdown_id)))
        select = Select(select_element)

        search_lower = search_text.lower().strip()
        matches = []
        for option in select.options:
            name = option.text.strip()
            if name and search_lower in name.lower():
                matches.append(name)

        return matches

    except Exception as e:
        print(f"Error in get_matching_countries: {e}")
        return []


def run_scraper(data_type, country, user_year):
    driver = None
    try:
        driver = setup_driver()
        is_import = data_type.lower() == "import"

        wait = _navigate_to_form(driver, is_import)

        year_id      = "EidbYearcwaci"     if is_import else "EidbYearcwace"
        country_id   = "EidbCntcwaci"      if is_import else "EidbCntcwace"
        currency_id  = "EidbReportcwaci"   if is_import else "EidbReportcwace"
        commodity_id = "EidbComLevelcwaci" if is_import else "EidbComLevelcwace"

        # SELECT YEAR
        wait.until(EC.presence_of_element_located((By.ID, year_id)))
        year_dropdown = Select(driver.find_element(By.ID, year_id))
        year_selected = False
        for opt in year_dropdown.options:
            if user_year in opt.text:
                opt.click()
                year_selected = True
                print(f"✅ Year selected: {opt.text}")
                break

        if not year_selected:
            available = [o.text for o in year_dropdown.options]
            raise Exception(f"Year '{user_year}' not found. Available: {available}")

        time.sleep(0.5)

        # WAIT FOR COUNTRY DROPDOWN
        wait.until(lambda d: len(Select(d.find_element(By.ID, country_id)).options) > 1)

        # SELECT COUNTRY
        country_element = driver.find_element(By.ID, country_id)
        country_select = Select(country_element)
        matched_value = None
        matched_name = None
        country_upper = country.upper().strip()

        for opt in country_select.options:
            name = opt.text.strip()
            value = opt.get_attribute("value")
            if value and name.upper() == country_upper:
                matched_value = value
                matched_name = name
                break

        if not matched_value:
            for opt in country_select.options:
                name = opt.text.strip()
                value = opt.get_attribute("value")
                if value and country_upper in name.upper():
                    matched_value = value
                    matched_name = name
                    break

        if not matched_value:
            raise Exception(f"Country '{country}' not found in dropdown")

        Select(driver.find_element(By.ID, country_id)).select_by_value(matched_value)
        print(f"✅ Country selected: {matched_name}")
        time.sleep(0.5)

        # CURRENCY USD
        Select(driver.find_element(By.ID, currency_id)).select_by_value("2")
        time.sleep(0.3)

        # COMMODITY 8 digit
        Select(driver.find_element(By.ID, commodity_id)).select_by_value("8")
        time.sleep(0.3)

        # SUBMIT
        buttons = driver.find_elements(By.TAG_NAME, "button")
        driver.execute_script("arguments[0].click();", buttons[1])
        print("⏳ Loading data...")

        # WAIT FOR RESULT
        wait.until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".buttons-excel")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'No data')]")),
            )
        )
        time.sleep(3)

        if "No data" in driver.page_source or "no record" in driver.page_source.lower():
            raise Exception(f"No data available for {country} {data_type} {user_year}")

        # DOWNLOAD
        before_files = set(os.listdir(DOWNLOAD_DIR))
        buttons = driver.find_elements(By.TAG_NAME, "button")
        driver.execute_script("arguments[0].click();", buttons[2])
        print("📥 Download started...")

        timeout = 30
        start = time.time()
        new_file = None
        while time.time() - start < timeout:
            after_files = set(os.listdir(DOWNLOAD_DIR))
            diff = after_files - before_files
            if diff:
                candidate = diff.pop()
                if not candidate.endswith(".crdownload"):
                    new_file = candidate
                    break
            time.sleep(1)

        if not new_file:
            raise Exception("File download timed out")

        old_path = os.path.join(DOWNLOAD_DIR, new_file)
        safe_name = (matched_name or country).replace(" ", "_")
        file_name = f"{data_type.capitalize()}-{safe_name}-{user_year}.xlsx"
        new_path = os.path.join(DOWNLOAD_DIR, file_name)
        safe_rename(old_path, new_path)

        print(f"✅ File ready: {new_path}")
        return new_path

    except Exception as e:
        print(f"Error in run_scraper: {e}")
        raise
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass