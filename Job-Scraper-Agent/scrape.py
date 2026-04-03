import re
import os
import math
import random
import logging
import asyncio

import pandas as pd
from tqdm import tqdm
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

#Logging 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# CONFIGURATION

HEADLESS    = False       # False = watch browser live
OUTPUT_FILE = "results.csv"
TIMEOUT     = 45_000
PAGE_DELAY  = (2, 3)
SCREENSHOT  = True
JOBS_PER_PAGE = 30        # shows 30 cards per page

BASE_SEARCH_URL = (
    "https://www.welcometothejungle.com/en/jobs"
    "?query=Business"
    "&refinementList%5Boffices.country_code%5D%5B%5D=US"
    "&page={page}"
)

CSV_HEADERS = [
    "Job_Title",
    "Company_Title",
    "Company_Slogan",
    "Job_Type",
    "Location",
    "Work_Location",
    "Industry",
    "Employes_Count",   
    "Posted_Ago",
    "Job_Link",
]

# Known contract type keywords (lowercase for matching)
CONTRACT_TYPES = [
    "permanent contract", "internship", "freelance", "fixed-term contract",
    "work-study", "apprenticeship", "vie", "temporary", "part-time",
    "fixed term", "contractor",
]

# Known work-mode keywords (lowercase for matching)
WORK_MODES = [
    "fully-remote", "full remote", "remote", "hybrid",
    "few days at home", "on-site", "onsite", "telework",
    "days at home",
]

# UTILITY

async def save_screenshot(page, name: str):
    if not SCREENSHOT:
        return
    os.makedirs("screenshots", exist_ok=True)
    path = f"screenshots/{name}.png"
    await page.screenshot(path=path, full_page=False)
    log.info(f" {path}")


async def try_click(page, selectors: list, label="button", timeout=4000):
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=timeout):
                await btn.click()
                log.info(f" {label} closed → {sel}")
                await page.wait_for_timeout(1500)
                return True
        except Exception:
            continue
    return False

# STEP 6: CLEANING

def clean_posted_ago(raw: str) -> str:
    """Rule (i): 'yesterday' → '1 days ago'"""
    if raw.strip().lower() == "yesterday":
        return "1 days ago"
    return raw.strip()


def clean_employee_count(raw: str) -> str:
    """Rule (ii): '150 employees' → '150'"""
    if not raw:
        return raw
    if "employee" in raw.lower():
        cleaned = re.sub(r"\s*employees?\s*", "", raw, flags=re.IGNORECASE).strip()
        return cleaned.strip(",. ")
    return raw.strip()

# CARD DATA EXTRACTOR (JavaScript running inside the browser)

EXTRACT_JS = r"""
() => {
    const CONTRACT_TYPES = [
        'permanent contract', 'internship', 'freelance', 'fixed-term contract',
        'work-study', 'apprenticeship', 'vie', 'temporary', 'part-time',
        'fixed term', 'contractor'
    ];
    const WORK_MODES = [
        'fully-remote', 'full remote', 'remote', 'hybrid',
        'few days at home', 'on-site', 'onsite', 'telework', 'days at home'
    ];

    const cards = document.querySelectorAll('li[data-testid="search-results-list-item-wrapper"]');

    return Array.from(cards).map(card => {

        // FIXED JOB TITLE + LINK
                // JOB TITLE + LINK
        let jobTitle = '';
        let jobLink = '';

        const lines = card.innerText
            .split('\n')
            .map(x => x.trim())
            .filter(Boolean);

        // The first visible text line on the card is the job title
        if (lines.length > 0) {
            jobTitle = lines[0];
        }

        // Get the real job URL
        const anchors = card.querySelectorAll('a[href]');
        for (const a of anchors) {
            const href = a.getAttribute('href') || '';
            if (href.includes('/jobs/')) {
                jobLink = href.startsWith('http')
                    ? href
                    : 'https://www.welcometothejungle.com' + href;
                break;
            }
        }

        // Fallback: derive title from URL slug if needed
        if (!jobTitle && jobLink) {
            const slug = jobLink.split('/jobs/').pop().split(/[?#]/)[0] || '';
            jobTitle = slug.split('_')[0].replace(/-/g, ' ').trim();
        }

        // COMPANY NAME (UNCHANGED)
        
        let companyTitle = '';
        const imgs = card.querySelectorAll('img[alt]');
        for (const img of imgs) {
            const alt = img.getAttribute('alt').trim();
            if (alt && alt.length > 1 && alt.length < 80 && !alt.includes('logo')) {
                companyTitle = alt;
                break;
            }
        }

        if (!companyTitle) {
            const cn = card.querySelector('[class*="company"] span, [class*="Company"] span');
            if (cn) companyTitle = cn.innerText.trim();
        }

        // SLOGAN
        
        let companySlogan = '';
        const ps = card.querySelectorAll('p');
        for (const p of ps) {
            const txt = p.innerText.trim();
            if (txt.length > 10) {
                companySlogan = txt;
                break;
            }
        }

        // POSTED TIME
        
        const timeEl = card.querySelector('time');
        const postedAgoRaw = timeEl ? timeEl.innerText.trim() : '';

        // TAG EXTRACTION (UNCHANGED)
        
        const exclude = new Set([jobTitle, companyTitle, companySlogan, postedAgoRaw].map(s => s.trim()).filter(Boolean));

        const allTexts = [];
        const walker = document.createTreeWalker(card, NodeFilter.SHOW_TEXT, null);
        let n;
        while (n = walker.nextNode()) {
            const t = n.textContent.trim();
            if (t && t.length > 1 && t.length < 80 && !exclude.has(t)) {
                allTexts.push(t);
            }
        }

        const seen = new Set();
        const tagLines = allTexts.filter(t => {
            if (seen.has(t)) return false;
            seen.add(t);
            return true;
        });

        let jobType = '', location = '', workLocation = '', industry = '', empCount = '';
        let postedAgo = postedAgoRaw;

        for (const line of tagLines) {
            const lower = line.toLowerCase();

            if (!empCount && /\d[\d,.+\-]*\s*employees?/i.test(line)) {
                empCount = line;
                continue;
            }
            if (!postedAgo && /(days? ago|hours? ago|minutes? ago|just now|yesterday|today)/i.test(line)) {
                postedAgo = line;
                continue;
            }
            if (!jobType && CONTRACT_TYPES.some(ct => lower.includes(ct))) {
                jobType = line;
                continue;
            }
            if (!workLocation && WORK_MODES.some(wm => lower.includes(wm))) {
                workLocation = line;
                continue;
            }
            if (!industry && (
                line.includes('/') ||
                /\b(tech|software|saas|logistics|finance|fintech|healthcare|retail|automotive|media|marketing|education|consulting|estate|manufacturing|energy|transport)\b/i.test(line)
            )) {
                industry = line;
                continue;
            }
            if (!location &&
                /^[A-Z][a-zA-Z\s,]+$/.test(line) &&
                line.length <= 30 &&
                !line.includes('/') &&
                !/\d/.test(line)
            ) {
                location = line;
                continue;
            }
        }

        return {
            Job_Title: jobTitle,
            Company_Title: companyTitle,
            Company_Slogan: companySlogan,
            Job_Type: jobType,
            Location: location,
            Work_Location: workLocation,
            Industry: industry,
            Employes_Count: empCount,
            Posted_Ago: postedAgo,
            Job_Link: jobLink
        };
    });
}
"""

GET_TOTAL_JOBS_JS = r"""
() => {
    const els = document.querySelectorAll(
        '[data-testid="total-count"], [class*="count"], [class*="total"], ' +
        'h2, h3, span, div'
    );
    for (const el of els) {
        const txt = el.innerText.trim();
        const m = txt.match(/^(\d+)$/);
        if (m && parseInt(m[1]) > 0 && parseInt(m[1]) < 10000) {
            const parent = el.closest('[class]');
            if (parent && parent.innerText.includes('Job')) {
                return parseInt(m[1]);
            }
        }
    }
    const bodyText = document.body.innerText;
    const m2 = bodyText.match(/Jobs\s+(\d+)/);
    if (m2) return parseInt(m2[1]);
    return 0;
}
"""

# MAIN SCRAPER

async def run_scraper() -> list[dict]:
    all_jobs = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=HEADLESS,
            slow_mo=60 if not HEADLESS else 0,
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )
        page = await context.new_page()

        #STEP 1: Load page 1 
        url_p1 = BASE_SEARCH_URL.format(page=1)
        log.info(f"Step 1: Loading → {url_p1}")
        await page.goto(url_p1, timeout=TIMEOUT, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        await save_screenshot(page, "01_initial_load")

        #Close India disclaimer (modal with "Stay on the current website") ──
        closed = await try_click(page, [
            "button:has-text('Stay on the current website')",
            "button[aria-label='Close']",
            "button[aria-label='close']",
            "button:has-text('Close')",
        ], label="India disclaimer", timeout=5000)
        if closed:
            await page.wait_for_timeout(1500)

        #Close cookie banner ("OK for me" from Axeptio) ─────────────────
        closed2 = await try_click(page, [
            "button:has-text('OK for me')",
            "#axeptio_btn_acceptAll",
            ".axeptio_btn_acceptAll",
            "button:has-text('Accept all')",
            "button:has-text('Accept')",
            "[class*='axeptio'] button",
        ], label="Cookie banner", timeout=5000)
        if closed2:
            await page.wait_for_timeout(1500)

        await save_screenshot(page, "02_popups_closed")

        #STEP 4: Wait for job cards 
        log.info("Step 4: Waiting for job results...")
        try:
            await page.wait_for_selector(
                "li[data-testid='search-results-list-item-wrapper']",
                timeout=TIMEOUT
            )
        except PWTimeout:
            log.warning("  Timeout on page 1 — continuing anyway.")

        await page.wait_for_timeout(2000)

        #Detect total number of jobs
        total_jobs = await page.evaluate(GET_TOTAL_JOBS_JS)
        if total_jobs > 0:
            total_pages = math.ceil(total_jobs / JOBS_PER_PAGE)
            log.info(f"  Total jobs: {total_jobs} → {total_pages} pages to scrape.")
        else:
            total_pages = 20    # safe upper bound; will stop when 0 cards found
            log.warning("  Could not detect job count — will scrape until empty page.")

        await save_screenshot(page, "03_results_loaded")

        #STEP 5: Iterate all pages via URL
        log.info("Step 5: Scraping all pages...")

        for pg in range(1, total_pages + 1):
            if pg > 1:
                url_pg = BASE_SEARCH_URL.format(page=pg)
                log.info(f"  Navigating to page {pg}/{total_pages}: {url_pg}")
                await page.goto(url_pg, timeout=TIMEOUT, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

                # Wait for cards
                try:
                    await page.wait_for_selector(
                        "li[data-testid='search-results-list-item-wrapper']",
                        timeout=15000
                    )
                except PWTimeout:
                    log.warning(f"  No cards found on page {pg} — stopping.")
                    break

                await page.wait_for_timeout(2000)

            # Scroll down to load all lazy-loaded cards
            for _ in range(4):
                await page.evaluate("window.scrollBy(0, 800)")
                await page.wait_for_timeout(400)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1200)

            #Extract cards via JS
            page_jobs = await page.evaluate(EXTRACT_JS)
            valid = [j for j in page_jobs if j.get("Job_Title") or j.get("Company_Title")]

            if not valid:
                log.info(f"  Page {pg}: 0 jobs — reached end.")
                break

            log.info(f"  Page {pg}/{total_pages}: {len(valid)} jobs.")

            # Print sample from first page to verify fields
            if pg == 1 and valid:
                s = valid[0]
                log.info(f"  ── SAMPLE JOB (page 1, card 1) ──")
                log.info(f"     Title       : {s['Job_Title']}")
                log.info(f"     Company     : {s['Company_Title']}")
                log.info(f"     Slogan      : {s['Company_Slogan']}")
                log.info(f"     Job Type    : {s['Job_Type']}")
                log.info(f"     Location    : {s['Location']}")
                log.info(f"     Work Mode   : {s['Work_Location']}")
                log.info(f"     Industry    : {s['Industry']}")
                log.info(f"     Employees   : {s['Employes_Count']}")
                log.info(f"     Posted      : {s['Posted_Ago']}")
                log.info(f"     Link        : {s['Job_Link'][:60]}...")
                log.info(f"     Debug tags  : {s.get('_debug_tags','')}")

            all_jobs.extend(valid)
            await save_screenshot(page, f"page_{pg:02d}_done")

            # Polite delay between pages
            if pg < total_pages:
                delay = random.uniform(*PAGE_DELAY)
                await page.wait_for_timeout(int(delay * 1000))

        await browser.close()

    return all_jobs


# STEP 6: CLEANING

def apply_cleaning(jobs: list[dict]) -> list[dict]:
    for job in jobs:
        job["Posted_Ago"]     = clean_posted_ago(job.get("Posted_Ago", ""))
        job["Employes_Count"] = clean_employee_count(job.get("Employes_Count", ""))
        job.pop("_debug_tags", None)    # remove debug field before saving
    return jobs

# STEP 7: SAVE CSV

def save_csv(jobs: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(jobs)
    for col in CSV_HEADERS:
        if col not in df.columns:
            df[col] = ""
    df = df[CSV_HEADERS]
    df.drop_duplicates(subset=["Job_Link"], keep="first", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    log.info(f" Saved {len(df)} records → '{OUTPUT_FILE}'")
    return df

# STEP 8: CONTEST ANSWERS

def parse_max_emp(val: str):
    if not val:
        return None
    nums = re.findall(r"\d[\d,]*", str(val).replace(",", ""))
    return max(int(n) for n in nums) if nums else None


def print_answers(df: pd.DataFrame):
    total      = len(df)
    ny         = int(df["Location"].str.contains("New York", case=False, na=False).sum())
    df["_e"]   = df["Employes_Count"].apply(parse_max_emp)
    more_200   = int((df["_e"] > 200).sum())
    less_200   = int((df["_e"] < 200).sum())
    perm       = int(df["Job_Type"].str.contains("Permanent", case=False, na=False).sum())
    intern_cnt = int(df["Job_Type"].str.contains("Internship", case=False, na=False).sum())
    df.drop(columns=["_e"], inplace=True)

    print("\n" + "=" * 60)
    print("  CONTEST ANSWERS  —  copy into Google Form")
    print("=" * 60)
    print(f"  (a) Total jobs                     : {total}")
    print(f"  (b) Total jobs in New York         : {ny}")
    print(f"  (c) Companies > 200 employees      : {more_200}")
    print(f"  (d) Companies < 200 employees      : {less_200}")
    print(f"  (e) Permanent Contract jobs        : {perm}")
    print(f"  (f) Internship jobs                : {intern_cnt}")
    print("=" * 60 + "\n")

# MAIN

def main():
    log.info("=" * 60)
    log.info("  WTTJ Scraper v4 — ReluConsultancy Hiring Challenge")
    log.info("=" * 60)

    raw   = asyncio.run(run_scraper())
    log.info(f"Raw records collected: {len(raw)}")

    clean = apply_cleaning(raw)
    df    = save_csv(clean)
    print_answers(df)

    log.info("Files ready: wttj_scraper.py  +  results.csv")


if __name__ == "__main__":
    main()