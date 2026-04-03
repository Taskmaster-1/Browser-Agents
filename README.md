# 🤖 Browser Agents

A collection of browser automation agents built with **Python + Playwright**. Each agent is a self-contained script that navigates real websites, handles dynamic content, bypasses popups, and extracts or interacts with data — just like a human would.

---

## 📦 Agents

### 🌿 Job Scraper Agent
**Folder:** `Job-Scraper-Agent/`

Scrapes job listings from any job portal. Handles popups, pagination, lazy-loading, and exports clean CSV data. Currently configured for [Welcome to the Jungle](https://www.welcometothejungle.com) but works on any site — just swap the URL and search keyword.

**Extracts:** Job title, company, slogan, contract type, location, remote policy, industry, employee count, posted date, job link.

```bash
cd Job-Scraper-Agent
pip install -r requirements.txt
playwright install chromium
python scrape.py
```

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| [Playwright](https://playwright.dev/python/) | Browser automation — renders JavaScript, clicks buttons, fills forms |
| [pandas](https://pandas.pydata.org/) | Data processing and CSV export |
| [tqdm](https://tqdm.github.io/) | Progress bars |

---

## 🗂️ Repo Structure

```
Browser-Agents/
│
├── Job-Scraper-Agent/        # Scrapes job listings from any job portal
│   ├── scrape.py
│   ├── requirements.txt
│   └── README.md
│
└── README.md                 # You are here
```

> More agents coming soon.

---

## 🚀 Getting Started

Each agent is fully self-contained. Navigate into any agent folder and follow its own `README.md` for setup and usage instructions.

---

## 💡 What Are Browser Agents?

Browser agents are scripts that control a real web browser programmatically. Unlike simple HTTP scrapers, they can:

- ✅ Execute JavaScript and wait for dynamic content to load
- ✅ Click buttons, close popups, fill in search boxes
- ✅ Navigate across multiple pages automatically
- ✅ Handle cookie banners, modals, and region redirects
- ✅ Scroll pages to trigger lazy-loaded content
- ✅ Run visibly (watch it work) or silently in the background

---

## ⚠️ Disclaimer

All agents in this repo are for educational and research purposes only. Always respect a website's `robots.txt` and Terms of Service. Use reasonable request delays and do not overload servers.

---

## 👤 Author

**Vivek Yadav**  
[GitHub](https://github.com/Taskmaster-1) · [LinkedIn](https://www.linkedin.com/in/taskmaster)