# 🌿 Job Scraper Agent

A powerful, flexible web scraper built with **Python + Playwright** that extracts job listings from any job portal. Simply swap the target URL and search keyword to scrape any website for any role.

> Built as part of the **Data Extraction Engineer Hiring Challenge**.

---

## ✨ Features

- 🔄 **Universal** — works on any job portal, just change the URL and search keyword
- 📄 **Full pagination** — automatically scrapes every page, not just the first
- 🧹 **Data cleaning** — normalizes employee counts, posted dates, and more
- 💾 **CSV export** — clean, structured output ready for analysis
- 📸 **Screenshot debugging** — saves screenshots at every step so you can see what the browser is doing
- 🛡️ **Anti-detection** — realistic user-agent and human-like delays between pages
- 🖥️ **Visible browser mode** — watch the scraper navigate live in real time

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/Taskmaster-1/Browser-Agents.git
cd Browser-Agents
cd Job-Scraper-Agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

> ⚠️ `playwright install chromium` is a one-time step to download the browser binary.

### 3. Run the scraper

```bash
python scrape.py
```

Output will be saved as `results.csv` in the same folder.

---

## ⚙️ Scrape Any Site, Any Role

All settings are at the top of `scrape.py`. To target a **different job portal** or search for a **different role**, just update the URL:

```python
BASE_SEARCH_URL = (
    "https://www.welcometothejungle.com/en/jobs"
    "?query=Business"          # ← Change role here (e.g. "Data Engineer", "Marketing")
    "&refinementList%5Boffices.country_code%5D%5B%5D=US"   # ← Change country (GB, FR, DE...)
    "&page={page}"
)
```

### Examples

| Role | URL Change |
|---|---|
| Data Engineer | `?query=Data+Engineer` |
| Marketing Manager | `?query=Marketing+Manager` |
| Software Engineer | `?query=Software+Engineer` |
| United Kingdom jobs | `country_code%5D%5B%5D=GB` |
| French jobs | `country_code%5D%5B%5D=FR` |

### Other settings

| Setting | Default | Description |
|---|---|---|
| `HEADLESS` | `False` | `True` = silent, `False` = watch browser live |
| `OUTPUT_FILE` | `results.csv` | Output CSV filename |
| `PAGE_DELAY` | `(2, 3)` | Random delay in seconds between pages |
| `SCREENSHOT` | `True` | Save debug screenshots to `screenshots/` |
| `JOBS_PER_PAGE` | `30` | Jobs shown per page on the target site |

---

## 📁 Output Format

| Column | Description | Example |
|---|---|---|
| `Job_Title` | Title of the job posting | `Business Development Manager` |
| `Company_Title` | Name of the hiring company | `Botify` |
| `Company_Slogan` | Company tagline / description | `AI-powered platform for SEO` |
| `Job_Type` | Contract type | `Permanent contract` |
| `Location` | City / State | `New York` |
| `Work_Location` | Remote policy | `Hybrid` |
| `Industry` | Sector / Industry | `Software, SaaS` |
| `Employes_Count` | Number of employees | `150` |
| `Posted_Ago` | When the job was posted | `3 days ago` |
| `Job_Link` | Direct URL to the job listing | `https://...` |

---

## 🧹 Data Cleaning Rules

| Rule | Input | Output |
|---|---|---|
| Posted date | `yesterday` | `1 days ago` |
| Employee count | `150 employees` | `150` |
| Duplicates | Same `Job_Link` | Removed automatically |

---

## 📂 Project Structure

```
Job-Scraper-Agent/
│
├── scrape.py             # Main scraper script
├── requirements.txt      # Python dependencies
├── results.csv           # Output CSV (generated after run)
├── screenshots/          # Debug screenshots (generated after run)
│   ├── 01_initial_load.png
│   ├── 02_popups_closed.png
│   ├── 03_results_loaded.png
│   └── page_01_done.png ...
└── README.md
```

---

## 🐛 Debugging

Check the `screenshots/` folder first — a screenshot is saved at every step.

| Problem | Fix |
|---|---|
| `Executable doesn't exist` | Run `playwright install chromium` |
| 0 jobs found | Check `screenshots/01_initial_load.png` — a popup may be blocking |
| Fields empty in CSV | Site HTML may have changed — set `HEADLESS = False` to watch live |
| Only first page scraped | Check if site uses different pagination format |

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `playwright` | Browser automation for JavaScript-heavy pages |
| `pandas` | Data manipulation and CSV export |
| `tqdm` | Progress bars |

---

## ⚠️ Disclaimer

For educational and research purposes only.