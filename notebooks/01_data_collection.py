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

# Original 80-row dataset
INPUT_FILE = BASE_DIR / "BA_100_LinkedIn.xlsx"

# We NEVER overwrite the original file
OUTPUT_FILE = BASE_DIR / "BA_100_LinkedIn_HK.xlsx"


# ============================================================
# 2. EXACT 29-COLUMN SCHEMA
# ============================================================

COLUMNS = [
    "job_id",
    "country",
    "city",
    "job_title",
    "company_name",
    "industry",
    "source",
    "job_url",
    "date_posted",
    "date_collected",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_stated",
    "experience_min",
    "experience_max",
    "education",
    "excel",
    "sql",
    "python",
    "r",
    "tableau",
    "power_bi",
    "data_visualization",
    "ai_tools",
    "generative_ai",
    "chatgpt",
    "JD_text",
    "collector"
]


# ============================================================
# 3. CHECK INPUT FILE
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
# 4. READ EXISTING DATA
# ============================================================

df_old = pd.read_excel(INPUT_FILE)

print("\n" + "=" * 60)
print("EXISTING DATASET")
print("=" * 60)

print(f"Rows: {len(df_old)}")
print(f"Columns: {len(df_old.columns)}")

print("\nExisting country distribution:")
print(df_old["country"].value_counts(dropna=False))

# Make sure required columns exist
missing_columns = [c for c in COLUMNS if c not in df_old.columns]

if missing_columns:
    print("\nERROR: The following columns are missing:")
    print(missing_columns)
    input("\nPress Enter to exit...")
    raise SystemExit

# Keep exact column order
df_old = df_old[COLUMNS].copy()

# Existing URLs
existing_urls = set(
    df_old["job_url"]
    .dropna()
    .astype(str)
    .str.strip()
)

print(f"\nExisting LinkedIn URLs: {len(existing_urls)}")


# ============================================================
# 5. REQUEST SESSION
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
    "Accept": "text/html",
    "Connection": "keep-alive"
})


# ============================================================
# 6. LINKEDIN SEARCH SETTINGS
# ============================================================

SEARCH_KEYWORD = "Business Analyst"
LOCATION = "Hong Kong"

TARGET_HK = 20

SEARCH_URL = "https://www.linkedin.com/jobs/search/"

HEADERS_FOR_SEARCH = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9"
}


# ============================================================
# 7. FUNCTIONS
# ============================================================

def clean_text(text):
    """Clean whitespace."""
    if not text:
        return ""

    text = re.sub(r"\s+", " ", str(text))
    return text.strip()


def normalize_url(url):
    """Normalize LinkedIn job URL."""

    if not url:
        return ""

    url = url.strip()

    # Remove query parameters
    url = url.split("?")[0]

    # Remove trailing slash
    url = url.rstrip("/")

    return url


def is_excluded_title(title):
    """
    Exclude internships and clearly senior/management positions.
    """

    title_lower = title.lower().strip()

    # Internship
    internship_words = [
        "intern",
        "internship",
        "trainee"
    ]

    for word in internship_words:
        if word in title_lower:
            return True, f"Internship/Trainee: {word}"

    # Senior / management
    senior_patterns = [
        r"\bsenior\b",
        r"\bsr\.?\b",
        r"\blead\b",
        r"\bmanager\b",
        r"\bdirector\b",
        r"\bhead of\b",
        r"\bvice president\b",
        r"\bvp\b",
        r"\bchief\b",
        r"\bprincipal\b"
    ]

    for pattern in senior_patterns:
        if re.search(pattern, title_lower):
            return True, f"Senior/management title: {pattern}"

    return False, ""


def extract_skill(jd_text, patterns):
    """
    Return Yes if a skill is explicitly mentioned.
    """

    if not jd_text:
        return "No"

    text = jd_text.lower()

    for pattern in patterns:
        if re.search(pattern, text):
            return "Yes"

    return "No"


def extract_salary(text):
    """
    Extract explicitly stated salary ranges where possible.
    This is intentionally conservative.
    """

    if not text:
        return "", "", "", ""

    text_lower = text.lower()

    # HK salary examples:
    # HK$30,000 - HK$40,000
    # HKD 30,000 - 40,000
    # 30K - 40K
    # $30,000-$40,000

    patterns = [
        r"HK\$?\s*([\d,]+)\s*[-–to]+\s*HK\$?\s*([\d,]+)",
        r"HKD\s*([\d,]+)\s*[-–to]+\s*HKD?\s*([\d,]+)",
        r"HK\$?\s*([\d,]+)\s*[-–]\s*([\d,]+)",
        r"([\d,]+)\s*[kK]\s*[-–to]+\s*([\d,]+)\s*[kK]"
    ]

    for pattern in patterns:

        match = re.search(pattern, text, re.I)

        if match:

            try:
                value1 = float(match.group(1).replace(",", ""))
                value2 = float(match.group(2).replace(",", ""))

                # Convert K to full number
                if "k" in match.group(0).lower():
                    value1 *= 1000
                    value2 *= 1000

                return (
                    value1,
                    value2,
                    "HKD",
                    match.group(0)
                )

            except:
                pass

    # Single salary
    single_patterns = [
        r"HK\$?\s*([\d,]+)",
        r"HKD\s*([\d,]+)"
    ]

    for pattern in single_patterns:

        match = re.search(pattern, text, re.I)

        if match:

            try:
                value = float(match.group(1).replace(",", ""))

                return (
                    value,
                    value,
                    "HKD",
                    match.group(0)
                )

            except:
                pass

    return "", "", "", ""


def extract_experience(text):
    """
    Extract simple experience requirements.
    """

    if not text:
        return "", ""

    text_lower = text.lower()

    # Examples:
    # 2 years of experience
    # 3-5 years experience
    # minimum 2 years
    # at least 3 years

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

                    return (
                        int(match.group(1)),
                        int(match.group(2))
                    )

                value = int(match.group(1))

                if "+" in match.group(0):

                    return value, ""

                return value, value

            except:
                pass

    return "", ""


def extract_education(text):
    """
    Extract explicitly mentioned education level.
    """

    if not text:
        return ""

    text_lower = text.lower()

    if any(
        x in text_lower
        for x in [
            "master's degree",
            "master degree",
            "master’s degree",
            "mba"
        ]
    ):
        return "Master's"

    if any(
        x in text_lower
        for x in [
            "bachelor's degree",
            "bachelor degree",
            "bachelor’s degree",
            "undergraduate degree"
        ]
    ):
        return "Bachelor's"

    if any(
        x in text_lower
        for x in [
            "degree required",
            "university degree"
        ]
    ):
        return "Degree"

    return ""


def infer_industry(company, title, jd_text):

    text = (
        f"{company} "
        f"{title} "
        f"{jd_text[:5000]}"
    ).lower()

    industry_keywords = {

        "Financial Services": [
            "bank",
            "banking",
            "insurance",
            "wealth management",
            "asset management",
            "investment",
            "securities",
            "capital markets",
            "trading",
            "fintech",
            "financial"
        ],

        "Technology": [
            "software",
            "technology",
            "tech",
            "saas",
            "cloud",
            "ai",
            "artificial intelligence",
            "information technology"
        ],

        "Consulting": [
            "consulting",
            "consultancy",
            "advisory"
        ],

        "Healthcare": [
            "hospital",
            "healthcare",
            "medical",
            "pharmaceutical",
            "life sciences"
        ],

        "Retail": [
            "retail",
            "e-commerce",
            "ecommerce",
            "consumer"
        ],

        "Manufacturing": [
            "manufacturing",
            "industrial",
            "factory"
        ]
    }

    for industry, keywords in industry_keywords.items():

        for keyword in keywords:

            if keyword in text:
                return industry

    return "Other"


def extract_job_detail(url):

    """
    Try to access the public LinkedIn job page.

    If blocked, return empty JD rather than stopping the entire process.
    """

    try:

        response = session.get(
            url,
            headers=HEADERS_FOR_SEARCH,
            timeout=15
        )

        if response.status_code in [403, 429]:

            print(
                f"    Job detail blocked: HTTP {response.status_code}"
            )

            return ""

        if response.status_code != 200:

            return ""

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Main description containers
        selectors = [
            "div.show-more-less-html__markup",
            "div.description__text",
            "section.description",
            "div.jobs-description__content"
        ]

        for selector in selectors:

            element = soup.select_one(selector)

            if element:

                text = clean_text(
                    element.get_text(" ", strip=True)
                )

                if len(text) > 50:

                    return text

        # Fallback
        text = clean_text(
            soup.get_text(" ", strip=True)
        )

        # Keep only reasonable amount
        if len(text) > 100:

            return text[:15000]

    except Exception as e:

        print(
            f"    Detail page error: {type(e).__name__}"
        )

    return ""


def parse_job_cards(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    cards = soup.select(
        "div.base-card"
    )

    if not cards:

        cards = soup.select(
            "div.job-search-card"
        )

    jobs = []

    for card in cards:

        try:

            title_element = card.select_one(
                "h3.base-search-card__title"
            )

            company_element = card.select_one(
                "h4.base-search-card__subtitle"
            )

            location_element = card.select_one(
                "span.job-search-card__location"
            )

            url_element = card.select_one(
                "a.base-card__full-link"
            )

            date_element = card.select_one(
                "time"
            )

            if not title_element:

                continue

            title = clean_text(
                title_element.get_text()
            )

            company = clean_text(
                company_element.get_text()
                if company_element else ""
            )

            location = clean_text(
                location_element.get_text()
                if location_element else "Hong Kong"
            )

            url = ""

            if url_element:

                url = url_element.get(
                    "href",
                    ""
                )

            url = normalize_url(url)

            date_posted = ""

            if date_element:

                date_posted = (
                    date_element.get("datetime")
                    or clean_text(
                        date_element.get_text()
                    )
                )

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
# 8. SEARCH LINKEDIN
# ============================================================

print("\n" + "=" * 60)
print("HONG KONG BUSINESS ANALYST SEARCH")
print("=" * 60)

new_jobs = []
seen_urls = set()

# Up to 10 public pages
for page in range(10):

    if len(new_jobs) >= TARGET_HK:
        break

    start = page * 25

    params = {
        "keywords": SEARCH_KEYWORD,
        "location": LOCATION,
        "start": start
    }

    search_url = (
        SEARCH_URL
        + "?"
        + urlencode(params)
    )

    print("\n" + "=" * 60)
    print(
        f"Hong Kong BA search | page {page + 1}"
    )
    print("=" * 60)

    try:

        response = session.get(
            search_url,
            headers=HEADERS_FOR_SEARCH,
            timeout=20
        )

    except Exception as e:

        print(
            f"Search request error: {e}"
        )

        break

    print(
        f"HTTP status: {response.status_code}"
    )

    if response.status_code in [403, 429]:

        print(
            "\nLinkedIn temporarily blocked the request."
        )

        print(
            "The script will stop without bypassing the block."
        )

        break

    if response.status_code != 200:

        print(
            "Unexpected HTTP status."
        )

        break

    jobs = parse_job_cards(
        response.text
    )

    print(
        f"Job cards found: {len(jobs)}"
    )

    if not jobs:

        print(
            "No job cards found. Stopping."
        )

        break

    page_new = 0

    for i, job in enumerate(jobs):

        if len(new_jobs) >= TARGET_HK:
            break

        title = job["title"]
        company = job["company"]
        url = job["url"]

        # Skip duplicate URLs
        if url in existing_urls:

            continue

        if url in seen_urls:

            continue

        # Exclusion rule
        excluded, reason = is_excluded_title(
            title
        )

        if excluded:

            print(
                f"  SKIP: {title} | {reason}"
            )

            continue

        seen_urls.add(url)

        new_jobs.append(job)

        page_new += 1

        print(
            f"  {len(new_jobs):02d}. "
            f"{title} | {company}"
        )

    print(
        f"New eligible jobs from this page: {page_new}"
    )

    if page_new == 0:

        print(
            "No new eligible jobs on this page."
        )

        # Continue to next page rather than stopping immediately

    # polite delay
    time.sleep(
        random.uniform(2, 4)
    )


# ============================================================
# 9. CHECK SEARCH RESULT
# ============================================================

print("\n" + "=" * 60)
print("SEARCH RESULT")
print("=" * 60)

print(
    f"Hong Kong eligible jobs found: {len(new_jobs)}"
)

if len(new_jobs) < TARGET_HK:

    print(
        f"\nWARNING: Only {len(new_jobs)} "
        f"eligible Hong Kong jobs were collected."
    )

    print(
        "This can happen because senior/lead/internship "
        "jobs were excluded or LinkedIn blocked further pages."
    )


# ============================================================
# 10. PROCESS JOBS
# ============================================================

records = []

today = datetime.now().strftime(
    "%Y-%m-%d"
)

# Existing collector name
collector_name = "HK_LinkedIn"

for index, job in enumerate(new_jobs):

    print("\n" + "=" * 60)

    print(
        f"Processing: "
        f"{job['title']}"
    )

    print(
        f"[{index + 1}/{len(new_jobs)}]"
    )

    # --------------------------------------------------------
    # Get JD
    # --------------------------------------------------------

    jd_text = extract_job_detail(
        job["url"]
    )

    print(
        f"    JD length: {len(jd_text)}"
    )

    # --------------------------------------------------------
    # Salary
    # --------------------------------------------------------

    salary_min, salary_max, salary_currency, salary_stated = (
        extract_salary(jd_text)
    )

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    experience_min, experience_max = (
        extract_experience(jd_text)
    )

    # --------------------------------------------------------
    # Education
    # --------------------------------------------------------

    education = extract_education(
        jd_text
    )

    # --------------------------------------------------------
    # Industry
    # --------------------------------------------------------

    industry = infer_industry(
        job["company"],
        job["title"],
        jd_text
    )

    # --------------------------------------------------------
    # Skills
    # --------------------------------------------------------

    excel = extract_skill(
        jd_text,
        [
            r"\bexcel\b",
            r"microsoft excel"
        ]
    )

    sql = extract_skill(
        jd_text,
        [
            r"\bsql\b",
            r"sql server",
            r"mysql",
            r"postgresql"
        ]
    )

    python_skill = extract_skill(
        jd_text,
        [
            r"\bpython\b"
        ]
    )

    r_skill = extract_skill(
        jd_text,
        [
            r"\br programming\b",
            r"\br language\b",
            r"\br studio\b"
        ]
    )

    tableau = extract_skill(
        jd_text,
        [
            r"\btableau\b"
        ]
    )

    power_bi = extract_skill(
        jd_text,
        [
            r"power\s*bi",
            r"microsoft power bi"
        ]
    )

    data_visualization = extract_skill(
        jd_text,
        [
            r"data visualization",
            r"data visualisation",
            r"data visualization tools",
            r"visualization"
        ]
    )

    ai_tools = extract_skill(
        jd_text,
        [
            r"\bartificial intelligence\b",
            r"\bai tools\b",
            r"\bmachine learning\b",
            r"\bai\b"
        ]
    )

    generative_ai = extract_skill(
        jd_text,
        [
            r"generative ai",
            r"\bgenai\b",
            r"gen ai"
        ]
    )

    chatgpt = extract_skill(
        jd_text,
        [
            r"\bchatgpt\b",
            r"openai"
        ]
    )

    # --------------------------------------------------------
    # City
    # --------------------------------------------------------

    location_text = job["location"]

    if "kowloon" in location_text.lower():

        city = "Kowloon"

    elif "new territories" in location_text.lower():

        city = "New Territories"

    else:

        city = "Hong Kong"

    # --------------------------------------------------------
    # Build record
    # --------------------------------------------------------

    record = {

        "job_id": "",

        "country": "Hong Kong",

        "city": city,

        "job_title": job["title"],

        "company_name": job["company"],

        "industry": industry,

        "source": "LinkedIn",

        "job_url": job["url"],

        "date_posted": job["date_posted"],

        "date_collected": today,

        "salary_min": salary_min,

        "salary_max": salary_max,

        "salary_currency": salary_currency,

        "salary_stated": salary_stated,

        "experience_min": experience_min,

        "experience_max": experience_max,

        "education": education,

        "excel": excel,

        "sql": sql,

        "python": python_skill,

        "r": r_skill,

        "tableau": tableau,

        "power_bi": power_bi,

        "data_visualization": data_visualization,

        "ai_tools": ai_tools,

        "generative_ai": generative_ai,

        "chatgpt": chatgpt,

        "JD_text": jd_text,

        "collector": collector_name
    }

    records.append(record)

    # Small delay
    time.sleep(
        random.uniform(1, 2)
    )


# ============================================================
# 11. CREATE NEW DATAFRAME
# ============================================================

df_new = pd.DataFrame(
    records,
    columns=COLUMNS
)

print("\n" + "=" * 60)
print("NEW HONG KONG DATA")
print("=" * 60)

print(
    f"New rows: {len(df_new)}"
)


# ============================================================
# 12. COMBINE OLD + NEW
# ============================================================

df_combined = pd.concat(
    [
        df_old,
        df_new
    ],
    ignore_index=True
)

# Make sure exact column order
df_combined = df_combined[
    COLUMNS
].copy()


# ============================================================
# 13. REMOVE DUPLICATES
# ============================================================

before_dedup = len(
    df_combined
)

df_combined["job_url"] = (
    df_combined["job_url"]
    .astype(str)
    .str.strip()
)

df_combined = (
    df_combined
    .drop_duplicates(
        subset=["job_url"],
        keep="first"
    )
    .reset_index(drop=True)
)

after_dedup = len(
    df_combined
)

print("\nDuplicate URLs removed:")
print(
    before_dedup - after_dedup
)


# ============================================================
# 14. RENUMBER JOB IDS
# ============================================================

df_combined["job_id"] = [
    f"BA{i:04d}"
    for i in range(
        1,
        len(df_combined) + 1
    )
]


# ============================================================
# 15. FINAL CHECK
# ============================================================

print("\n" + "=" * 60)
print("FINAL DATASET CHECK")
print("=" * 60)

print(
    f"Rows: {len(df_combined)}"
)

print(
    f"Columns: {len(df_combined.columns)}"
)

print("\nCountry distribution:")

print(
    df_combined["country"]
    .value_counts()
)


# Check columns
print("\nColumn check:")

if list(df_combined.columns) == COLUMNS:

    print(
        "OK - exact 29-column schema."
    )

else:

    print(
        "WARNING - column mismatch."
    )


# ============================================================
# 16. SAFE OUTPUT FILE
# ============================================================

# IMPORTANT:
# Never overwrite the original 80-row file.

output_file = OUTPUT_FILE

# If the output file already exists and is locked,
# automatically create another filename.

if output_file.exists():

    try:

        # Test whether the file can be opened for append
        with open(
            output_file,
            "a"
        ):
            pass

    except PermissionError:

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        output_file = (
            BASE_DIR
            / f"BA_100_LinkedIn_HK_{timestamp}.xlsx"
        )

        print(
            "\nExisting output file is currently open."
        )

        print(
            "Saving to a new filename instead:"
        )

        print(
            output_file
        )


# ============================================================
# 17. SAVE
# ============================================================

try:

    df_combined.to_excel(
        output_file,
        index=False,
        engine="openpyxl"
    )

except PermissionError:

    # Second fallback
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    fallback_file = (
        BASE_DIR
        / f"BA_100_LinkedIn_FINAL_{timestamp}.xlsx"
    )

    print(
        "\nThe first output file is locked."
    )

    print(
        "Saving to fallback file:"
    )

    print(
        fallback_file
    )

    df_combined.to_excel(
        fallback_file,
        index=False,
        engine="openpyxl"
    )

    output_file = fallback_file


# ============================================================
# 18. SUCCESS
# ============================================================

print("\n" + "=" * 60)
print("SUCCESS")
print("=" * 60)

print(
    f"Final rows: {len(df_combined)}"
)

print(
    f"Final columns: {len(df_combined.columns)}"
)

print(
    f"Hong Kong rows added: {len(df_new)}"
)

print(
    "\nFinal country distribution:"
)

print(
    df_combined["country"]
    .value_counts()
)

print(
    "\nOutput file:"
)

print(
    output_file
)

print("\nOriginal file was NOT overwritten.")

print("\nDone.")

input(
    "\nPress Enter to exit..."
)