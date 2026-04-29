#!/usr/bin/env python3
"""
Fetch publications from Google Scholar and generate a JSON data file.
Used by GitHub Actions to keep the website's publication list in sync.

Usage:
    python scripts/update_publications.py

Output:
    scholar_publications.json  (in the repo root)
"""

import json
import os
import sys
import time

# ---------------------------------------------------------------------------
# Configuration — change these to match your profile
# ---------------------------------------------------------------------------
SCHOLAR_ID = "HC7mkqgAAAAJ"          # Your Google Scholar user ID
OUTPUT_FILE = "scholar_publications.json"
YOUR_LAST_NAME = "Wang"               # Used to detect first-authorship
YOUR_FIRST_INITIAL = "Z"

# Manual entries that won't appear on Google Scholar (under review, working papers, etc.)
# These are merged into the final JSON so everything shows in one place.
MANUAL_ENTRIES = [
    {
        "title": "Where State, Market, and Community Meet: Village Doctors and the Governance of Rural Health in China",
        "authors": "Wang, Z., Gao, Z., Zou, X., Zhang, P., Rice, K., Bouey, J., & Liu, X.",
        "journal": "Revise & Resubmit: Social Science & Medicine",
        "year": "",
        "doi": "",
        "type": ["review", "first"],
        "badge": "R&R",
        "badge_class": "badge-review"
    },
    {
        "title": "Neo-Familist Values and Health-Seeking Behaviours Among Older Adults in Rural China",
        "authors": "Wang, Z., Wang, R., Liu, X., Zou, X., & Wu, B.",
        "journal": "Revise & Resubmit: Journal of Aging and Health",
        "year": "",
        "doi": "",
        "type": ["review", "first"],
        "badge": "R&R",
        "badge_class": "badge-review"
    },
    {
        "title": "Validation of a New Family Values Scale Among Older Chinese Adults",
        "authors": "Wang, Z., Sourial, N., Zou, X., Liu, X., Bergman, H., & Vedel, I.",
        "journal": "Revise & Resubmit: Family Relations",
        "year": "",
        "doi": "",
        "type": ["review", "first"],
        "badge": "R&R",
        "badge_class": "badge-review"
    },
    {
        "title": "The Fool, the Village, and the State: Situational Moral Economies and Co-Produced Authoritarianism in Rural Chinese Healthcare",
        "authors": "Wang, Z.",
        "journal": "Working paper",
        "year": "",
        "doi": "",
        "type": ["working", "first"],
        "badge": "",
        "badge_class": ""
    },
    {
        "title": "Structure, function, and performance: a comparative study of primary healthcare systems in China and Canada",
        "authors": "Wang, Z., Sourial, N., Bergman, H., Liu, X., & Vedel, I.",
        "journal": "Working paper",
        "year": "",
        "doi": "",
        "type": ["working", "first"],
        "badge": "",
        "badge_class": ""
    }
]

# Overrides: map a paper title (lowercased) to extra metadata.
# Use this to add badges, highlight status, or correct first-author detection.
# Titles are matched case-insensitively (partial match from the start).
OVERRIDES = {
    "older adults' experiences of health seeking in rural areas": {
        "extra_types": ["highlight"],
        "badge": "2025",
        "badge_class": "badge-lancet"
    },
    "evaluation of the mcgill-tongji blended education program": {
        "extra_types": ["highlight"],
        "badge": "Award Winner",
        "badge_class": "badge-award"
    },
    "longitudinal associations between self-reported vision impairment": {
        "extra_types": ["highlight"],
    },
    "time trends in tuberculosis mortality across the brics": {
        "extra_types": ["highlight"],
        "badge": "EClinicalMedicine",
        "badge_class": "badge-lancet"
    },
    "global, regional, and national burden of diabetes": {
        "extra_types": ["highlight"],
        "badge": "The Lancet",
        "badge_class": "badge-lancet"
    },
    "progress on catastrophic health expenditure in china": {
        "extra_types": ["first"],  # equal contribution
    },
}

# ---------------------------------------------------------------------------


def fetch_from_scholar():
    """Fetch publications from Google Scholar using the scholarly library."""
    try:
        from scholarly import scholarly, ProxyGenerator
    except ImportError:
        print("Installing scholarly...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "scholarly", "--quiet"])
        from scholarly import scholarly, ProxyGenerator

    # --- Set up proxy to avoid Google Scholar blocking GitHub Actions IPs ---
    # Option 1: Free proxies (no cost, but can be slow/unreliable)
    # Option 2: ScraperAPI (more reliable, requires API key set as GitHub secret)
    scraper_api_key = os.environ.get("SCRAPER_API_KEY", "")
    pg = ProxyGenerator()
    if scraper_api_key:
        print("Using ScraperAPI proxy...")
        pg.ScraperAPI(scraper_api_key)
    else:
        print("Using free proxies (set SCRAPER_API_KEY for better reliability)...")
        try:
            pg.FreeProxies()
        except Exception as e:
            print(f"Warning: Free proxy setup failed ({e}), trying without proxy...")
            pg = None
    if pg:
        scholarly.use_proxy(pg)

    print(f"Fetching Google Scholar profile: {SCHOLAR_ID}")

    # Retry logic for resilience
    max_retries = 3
    author = None
    for attempt in range(max_retries):
        try:
            author = scholarly.search_author_id(SCHOLAR_ID)
            author = scholarly.fill(author, sections=["publications"])
            break
        except Exception as e:
            print(f"  Attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                wait = 10 * (attempt + 1)
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
                # Try a new proxy
                if pg:
                    try:
                        pg.FreeProxies()
                        scholarly.use_proxy(pg)
                    except:
                        pass
            else:
                print("All retries failed. Exiting.")
                sys.exit(1)

    publications = []
    for pub in author.get("publications", []):
        # Fill each publication for full details
        try:
            filled = scholarly.fill(pub)
            time.sleep(1)  # Be polite to Google Scholar
        except Exception as e:
            print(f"  Warning: Could not fill details for '{pub.get('bib', {}).get('title', 'unknown')}': {e}")
            filled = pub

        bib = filled.get("bib", {})
        title = bib.get("title", "")
        authors = bib.get("author", "")
        journal = bib.get("journal", bib.get("venue", bib.get("publisher", "")))
        year = str(bib.get("pub_year", ""))
        volume = bib.get("volume", "")
        number = bib.get("number", "")
        pages = bib.get("pages", "")

        # Build journal string
        journal_str = journal
        if volume:
            journal_str += f", {volume}"
            if number:
                journal_str += f"({number})"
        if pages:
            journal_str += f", {pages}"
        if year:
            journal_str += f" ({year})"

        # Detect first authorship
        is_first = False
        if authors:
            # scholarly returns author names in various formats
            first_author = authors.split(",")[0].strip().split(" and ")[0].strip()
            if YOUR_LAST_NAME.lower() in first_author.lower():
                is_first = True

        pub_types = []
        if is_first:
            pub_types.append("first")

        # Check for overrides
        badge = year if year else ""
        badge_class = "badge-lancet" if year else ""
        title_lower = title.lower()
        for key, override in OVERRIDES.items():
            if title_lower.startswith(key):
                pub_types.extend(override.get("extra_types", []))
                if "badge" in override:
                    badge = override["badge"]
                if "badge_class" in override:
                    badge_class = override["badge_class"]
                break

        # Get DOI from pub_url or from bib
        doi = ""
        pub_url = filled.get("pub_url", "")
        if "doi.org" in pub_url:
            doi = pub_url
        elif bib.get("doi"):
            doi = f"https://doi.org/{bib['doi']}"

        publications.append({
            "title": title,
            "authors": authors,
            "journal": journal_str,
            "year": year,
            "doi": doi,
            "type": list(set(pub_types)),  # deduplicate
            "badge": badge,
            "badge_class": badge_class
        })

        print(f"  Fetched: {title[:60]}...")

    return publications


def main():
    print("=" * 60)
    print("Google Scholar Publication Sync")
    print("=" * 60)

    # Fetch from Google Scholar
    scholar_pubs = fetch_from_scholar()
    print(f"\nFetched {len(scholar_pubs)} publications from Google Scholar.")

    # Combine: scholar pubs first (sorted by year desc), then manual entries
    scholar_pubs.sort(key=lambda p: p.get("year", "0"), reverse=True)

    result = {
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scholar_id": SCHOLAR_ID,
        "scholar_url": f"https://scholar.google.com/citations?user={SCHOLAR_ID}&hl=en",
        "publications": scholar_pubs,
        "manual_entries": MANUAL_ENTRIES
    }

    # Write JSON
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), OUTPUT_FILE)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {len(scholar_pubs) + len(MANUAL_ENTRIES)} total entries to {OUTPUT_FILE}")
    print(f"  - {len(scholar_pubs)} from Google Scholar")
    print(f"  - {len(MANUAL_ENTRIES)} manual entries")
    print("Done!")


if __name__ == "__main__":
    main()
