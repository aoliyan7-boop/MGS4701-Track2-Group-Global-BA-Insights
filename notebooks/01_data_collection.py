import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
from pathlib import Path
from urllib.parse import urlencode
from datetime import datetime

# ============================================================
# 1. FILE SETTINGS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "BA_expand2_LinkedIn.xlsx"
OUTPUT_FILE = BASE_DIR / "BA_expand3_LinkedIn.xlsx"


# ============================================================
# 2. 25-COLUMN SCHEMA 【和你的Excel表头完全匹配】
# ============================================================
COLUMNS = [
    "Job_id",
    "Country",
    "City",
    "Job_Title",
    "Company_Name",
    "Industry",
    "Source",
    "Job_Url",
    "Date_Posted",
    "Date_Collected",
    "Salary_Min",
    "Salary_Max",
    "Salary_Currency",
    "Experience_Min",
    "Experience_Max",
    "Education",
    "Excel",
    "SQL",
    "Python",
    "R",
    "Tableau",
    "Power_BI",
    "AI_tools",
    "JD_text",
    "Collector"
]

# ============================================================
# 3. TARGET INCREMENT：每个国家5条
# ============================================================
LOC_CONFIG = [
    {"country": "Canada", "location": "Canada", "target": 30},
    {"country": "Australia", "location": "Australia", "target": 25},
    {"country": "Ireland", "location": "Ireland", "target": 15},
]


SEARCH_KEYWORD = "Business Analyst"
SEARCH_URL = "https://www.linkedin.com/jobs/search/"

# ============================================================
# FUNCTIONS
# ============================================================
def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", str(text))
    return text.strip()

def normalize_url(url):
    if not url:
        return ""
    url = str(url).strip()
    url = url.split("?")[0]
    url = url.rstrip("/")
    return url.lower()

def is_excluded_title(title):
    title_lower = title.lower().strip()
    internship_words = ["intern", "internship", "trainee"]
    for word in internship_words:
        if word in title_lower:
            return True, f"Internship/Trainee: {word}"
    senior_patterns = [
        r"\bsenior\b", r"\bsr\.?\b", r"\blead\b", r"\bmanager\b",
        r"\bdirector\b", r"\bhead of\b", r"\bvice president\b",
        r"\bvp\b", r"\bchief\b", r"\bprincipal\b"
    ]
    for pattern in senior_patterns:
        if re.search(pattern, title_lower):
            return True, f"Senior/management title: {pattern}"
    return False, ""

def extract_skill(jd_text, patterns):
    if not jd_text:
        return 0
    text = jd_text.lower()
    for pattern in patterns:
        if re.search(pattern, text):
            return 1
    return 0

def extract_salary(text, country):
    if not text:
        return "", "", ""
    text_lower = text.lower()
    if country == "Hong Kong":
        patterns = [
            r"HK\$?\s*([\d,]+)\s*[-–to]+\s*HK\$?\s*([\d,]+)",
            r"HKD\s*([\d,]+)\s*[-–to]+\s*HKD?\s*([\d,]+)",
            r"([\d,]+)\s*[kK]\s*[-–to]+\s*([\d,]+)\s*[kK]"
        ]
        currency = "HKD"
    elif country == "Singapore":
        patterns = [
            r"S\$?\s*([\d,]+)\s*[-–to]+\s*S\$?\s*([\d,]+)",
            r"SGD\s*([\d,]+)\s*[-–to]+\s*SGD?\s*([\d,]+)",
            r"([\d,]+)\s*[kK]\s*[-–to]+\s*([\d,]+)\s*[kK]"
        ]
        currency = "SGD"
    elif country == "United Kingdom":
        patterns = [
            r"£\s*([\d,]+)\s*[-–to]+\s*£\s*([\d,]+)",
            r"GBP\s*([\d,]+)\s*[-–to]+\s*GBP\s*([\d,]+)",
            r"([\d,]+)\s*[kK]\s*[-–to]+\s*([\d,]+)\s*[kK]"
        ]
        currency = "GBP"
    else:
        patterns = [
            r"\$\s*([\d,]+)\s*[-–to]+\s*\$\s*([\d,]+)",
            r"USD\s*([\d,]+)\s*[-–to]+\s*USD\s*([\d,]+)",
            r"([\d,]+)\s*[kK]\s*[-–to]+\s*([\d,]+)\s*[kK]"
        ]
        currency = "USD"

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                value1 = float(match.group(1).replace(",", ""))
                value2 = float(match.group(2).replace(",", ""))
                if "k" in match.group(0).lower():
                    value1 *= 1000
                    value2 *= 1000
                return value1, value2, currency
            except:
                pass
    return "", "", ""

def extract_experience(text):
    if not text:
        return "", ""
    text_lower = text.lower()
    patterns = [
        r"(\d+)\s*[-–]\s*(\d+)\s+years?\s+(?:of\s+)?experience",
        r"(\d+)\s*\+\s*years?\s+(?:of\s+)?experience",
        r"at least\s+(\d+)\s+years?\s+(?:of\s+)?experience",
        r"minimum\s+(\d+)\s+years?\s+(?:of\s+)?experience",
        r"(\d+)\s+years?\s+(?:of\s+)?experience"
    ]
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                if len(match.groups()) >= 2 and match.group(2):
                    return int(match.group(1)), int(match.group(2))
                value = int(match.group(1))
                if "+" in match.group(0):
                    return value, ""
                return value, value
            except:
                pass
    return "", ""

def extract_education(text):
    if not text:
        return ""
    text_lower = text.lower()
    if any(x in text_lower for x in ["master's degree", "master degree", "master’s degree", "mba"]):
        return "Master's"
    if any(x in text_lower for x in ["bachelor's degree", "bachelor degree", "bachelor’s degree", "undergraduate degree"]):
        return "Bachelor's"
    if any(x in text_lower for x in ["degree required", "university degree"]):
        return "Degree"
    return ""

def infer_industry(company, title, jd_text):
    text = f"{company} {title} {jd_text[:5000]}".lower()
    industry_keywords = {
        "Financial Services": ["bank", "banking", "insurance", "wealth management", "asset management",
                               "investment", "securities", "capital markets", "trading", "fintech", "financial"],
        "Technology": ["software", "technology", "tech", "saas", "cloud", "ai", "artificial intelligence", "information technology"],
        "Consulting": ["consulting", "consultancy", "advisory"],
        "Healthcare": ["hospital", "healthcare", "medical", "pharmaceutical", "life sciences"],
        "Retail": ["retail", "e-commerce", "ecommerce", "consumer"],
        "Manufacturing": ["manufacturing", "industrial", "factory"]
    }
    for industry, keywords in industry_keywords.items():
        for keyword in keywords:
            if keyword in text:
                return industry
    return "Other"

def extract_job_detail(url):
    try:
        response = session.get(url, headers=HEADERS_FOR_SEARCH, timeout=15)
        if response.status_code in [403, 429]:
            print(f"    Job detail blocked: HTTP {response.status_code}")
            return ""
        if response.status_code != 200:
            return ""
        soup = BeautifulSoup(response.text, "html.parser")
        selectors = [
            "div.show-more-less-html__markup",
            "div.description__text",
            "section.description",
            "div.jobs-description__content"
        ]
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = clean_text(element.get_text(" ", strip=True))
                if len(text) > 50:
                    return text
        text = clean_text(soup.get_text(" ", strip=True))
        if len(text) > 100:
            return text[:15000]
    except Exception as e:
        print(f"    Detail page error: {type(e).__name__}")
    return ""

def parse_job_cards(html):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.base-card")
    if not cards:
        cards = soup.select("div.job-search-card")
    jobs = []
    for card in cards:
        try:
            title_element = card.select_one("h3.base-search-card__title")
            company_element = card.select_one("h4.base-search-card__subtitle")
            location_element = card.select_one("span.job-search-card__location")
            url_element = card.select_one("a.base-card__full-link")
            date_element = card.select_one("time")
            if not title_element:
                continue
            title = clean_text(title_element.get_text())
            company = clean_text(company_element.get_text() if company_element else "")
            location = clean_text(location_element.get_text() if location_element else "")
            url = url_element.get("href", "") if url_element else ""
            url = normalize_url(url)
            date_posted = date_element.get("datetime") or clean_text(date_element.get_text()) if date_element else ""
            if title and url:
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": url,
                    "date_posted": date_posted
                })
        except Exception:
            continue
    return jobs

# ============================================================
# CHECK INPUT FILE
# ============================================================
print("=" * 60)
print("FILE CHECK")
print("=" * 60)
print("Script folder:")
print(BASE_DIR)
print("\nInput file:")
print(INPUT_FILE)
if not INPUT_FILE.exists():
    print("\nERROR: BA_100_LinkedIn.xlsx was not found.")
    print("\nPlease make sure this file is in the same folder as ba.py:")
    print(INPUT_FILE)
    input("\nPress Enter to exit...")
    raise SystemExit
print("\nInput file found.")

# ============================================================
# READ EXISTING DATA
# ============================================================
df_old = pd.read_excel(INPUT_FILE)
print("\n" + "=" * 60)
print("EXISTING DATASET")
print("=" * 60)
print(f"Rows: {len(df_old)}")
print(f"Columns: {len(df_old.columns)}")
print("\nExisting country distribution:")
print(df_old["Country"].value_counts(dropna=False))

missing_columns = [c for c in COLUMNS if c not in df_old.columns]
if missing_columns:
    print("\nERROR: The following columns are missing:")
    print(missing_columns)
    input("\nPress Enter to exit...")
    raise SystemExit
df_old = df_old[COLUMNS].copy()

existing_urls = set()
for raw_u in df_old["Job_Url"].dropna().astype(str):
    u_clean = normalize_url(raw_u)
    if u_clean:
        existing_urls.add(u_clean)

print(f"\nExisting normalized LinkedIn URLs (for deduplicate): {len(existing_urls)}")

# ============================================================
# REQUEST SESSION
# ============================================================
session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive"
})
HEADERS_FOR_SEARCH = session.headers.copy()

# ============================================================
# MAIN LOOP
# ============================================================
all_new_records = []
today = datetime.now().strftime("%Y-%m-%d")

for loc_cfg in LOC_CONFIG:
    country_name = loc_cfg["country"]
    loc_name = loc_cfg["location"]
    target_num = loc_cfg["target"]
    collector_tag = f"{country_name.replace(' ','_')}_LinkedIn"
    collected_this_loc = 0
    seen_urls_loc = set()

    print("\n" + "=" * 70)
    print(f"START SEARCH: {country_name} | Target this batch: {target_num}")
    print("=" * 70)

    for page in range(20):
        if collected_this_loc >= target_num:
            print(f"✅ {country_name} target {target_num} reached, move to next region.")
            break
        start = page * 25
        params = {
            "keywords": SEARCH_KEYWORD,
            "location": loc_name,
            "start": start
        }
        search_url = SEARCH_URL + "?" + urlencode(params)
        print(f"\n{country_name} | Page {page+1}, start={start}")
        try:
            resp = session.get(search_url, headers=HEADERS_FOR_SEARCH, timeout=20)
        except Exception as e:
            print(f"Search error: {e}")
            break
        print(f"HTTP {resp.status_code}")
        if resp.status_code in [403, 429]:
            print("❌ LinkedIn blocked, stop this region, keep collected jobs so far.")
            break
        if resp.status_code != 200:
            print("Unexpected status, skip this region.")
            break
        jobcards = parse_job_cards(resp.text)
        print(f"Cards found on page: {len(jobcards)}")
        if not jobcards:
            print("No job cards, stop this region.")
            break
        page_add = 0
        for job in jobcards:
            if collected_this_loc >= target_num:
                break
            j_title = job["title"]
            j_url = job["url"]
            if j_url in existing_urls or j_url in seen_urls_loc:
                continue
            excluded, reason = is_excluded_title(j_title)
            if excluded:
                print(f"  SKIP: {j_title} | {reason}")
                continue
            seen_urls_loc.add(j_url)
            print(f"  [{collected_this_loc+1}/{target_num}] {j_title} | {job['company']}")
            jd_text = extract_job_detail(j_url)
            salary_min, salary_max, salary_currency = extract_salary(jd_text, country_name)
            exp_min, exp_max = extract_experience(jd_text)
            edu = extract_education(jd_text)
            ind = infer_industry(job["company"], j_title, jd_text)

            excel = extract_skill(jd_text, [r"\bexcel\b", r"microsoft excel"])
            sql = extract_skill(jd_text, [r"\bsql\b", r"sql server", r"mysql", r"postgresql"])
            python_skill = extract_skill(jd_text, [r"\bpython\b"])
            r_skill = extract_skill(jd_text, [r"\br programming\b", r"\br language\b", r"\br studio\b"])
            tableau = extract_skill(jd_text, [r"\btableau\b"])
            power_bi = extract_skill(jd_text, [r"power\s*bi", r"microsoft power bi"])
            ai_tools = extract_skill(jd_text, [r"\bartificial intelligence\b", r"\bai tools\b", r"\bmachine learning\b", r"\bai\b"])

            city = job["location"]
            if country_name == "Hong Kong":
                if "kowloon" in city.lower():
                    city = "Kowloon"
                elif "new territories" in city.lower():
                    city = "New Territories"
                else:
                    city = "Hong Kong"
            elif country_name == "Singapore":
                city = "Singapore"

            rec = {
                "Job_id": "",
                "Country": country_name,
                "City": city,
                "Job_Title": j_title,
                "Company_Name": job["company"],
                "Industry": ind,
                "Source": "LinkedIn",
                "Job_Url": j_url,
                "Date_Posted": job["date_posted"],
                "Date_Collected": today,
                "Salary_Min": salary_min,
                "Salary_Max": salary_max,
                "Salary_Currency": salary_currency,
                "Experience_Min": exp_min,
                "Experience_Max": exp_max,
                "Education": edu,
                "Excel": excel,
                "SQL": sql,
                "Python": python_skill,
                "R": r_skill,
                "Tableau": tableau,
                "Power_BI": power_bi,
                "AI_tools": ai_tools,
                "JD_text": jd_text,
                "Collector": collector_tag
            }
            all_new_records.append(rec)
            collected_this_loc += 1
            page_add += 1
            time.sleep(random.uniform(4, 7))
        print(f"Page add: {page_add} | Total collected for {country_name}: {collected_this_loc}/{target_num}")
        time.sleep(random.uniform(6, 10))
    if collected_this_loc < target_num:
        print(f"⚠️ {country_name} only got {collected_this_loc}/{target_num}, shortage will NOT auto fill other regions")

# ============================================================
# Combine old + new
# ============================================================
df_new = pd.DataFrame(all_new_records, columns=COLUMNS)
print("\n" + "=" * 70)
print("AGGREGATED NEW JOBS SUMMARY")
print("=" * 70)
print(f"Total newly fetched eligible jobs: {len(df_new)}")

df_combined = pd.concat([df_old, df_new], ignore_index=True)
df_combined = df_combined[COLUMNS].copy()

before_dedup = len(df_combined)
df_combined["Job_Url"] = df_combined["Job_Url"].astype(str).str.strip()
df_combined = df_combined.drop_duplicates(subset=["Job_Url"], keep="first").reset_index(drop=True)
after_dedup = len(df_combined)
print(f"\nDuplicates removed in final dedup: {before_dedup - after_dedup}")

df_combined["Job_id"] = [f"BA{i:04d}" for i in range(1, len(df_combined)+1)]

print("\n" + "=" * 70)
print("FINAL DATASET CHECK")
print("=" * 70)
print(f"Final total rows: {len(df_combined)}")
print("\nCountry distribution:")
print(df_combined["Country"].value_counts())

if list(df_combined.columns) == COLUMNS:
    print("\n✅ Column schema check OK")
else:
    print("\n⚠️ Column mismatch warning")

# ============================================================
# Save
# ============================================================
output_file = OUTPUT_FILE
if output_file.exists():
    try:
        with open(output_file, "a"):
            pass
    except PermissionError:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = BASE_DIR / f"BA_expand_LinkedIn_{ts}.xlsx"
        print(f"\nTarget file locked, save to timestamped: {output_file}")
try:
    df_combined.to_excel(output_file, index=False, engine="openpyxl")
except PermissionError:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fallback = BASE_DIR / f"BA_expand_FALLBACK_{ts}.xlsx"
    print(f"\nFirst save failed, fallback to: {fallback}")
    df_combined.to_excel(fallback, index=False, engine="openpyxl")
    output_file = fallback

print("\n" + "=" * 70)
print("SAVE SUCCESS")
print("=" * 70)
print(f"Output path: {output_file}")
print("Original BA_100_LinkedIn.xlsx untouched.")
input("\nPress Enter to exit...")
