#!/usr/bin/env python3
"""
Fetch publications from Google Scholar via SerpAPI and generate a JSON data file.
Used by GitHub Actions to keep the website's publication list in sync.

Requires: SERPAPI_KEY environment variable (get free key at https://serpapi.com)

Usage:
    python scripts/update_publications.py

Output:
    scholar_publications.json  (in the repo root)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse

# ---------------------------------------------------------------------------
# Configuration — change these to match your profile
# ---------------------------------------------------------------------------
SCHOLAR_ID = "HC7mkqgAAAAJ"          # Your Google Scholar user ID
OUTPUT_FILE = "scholar_publications.json"
YOUR_LAST_NAME = "Wang"               # Used to detect first-authorship
YOUR_FIRST_INITIAL = "Z"

# Manual entries that won't appear on Google Scholar (under review, working papers, etc.)
MANUAL_ENTRIES = [
    {
        "title": "Where State, Market, and Community Meet: Village Doctors and the Governance of Rural Health in China",
        "authors": "Wang, Z., Gao, Z., Zou, X., Zhang, P., Ma, X., Rice, K., Bouey, J., & Liu, X.",
        "journal": "Social Science & Medicine, 119294 (2026)",
        "year": "2026",
        "doi": "",
        "scholar_link": "",
        "type": ["first"],
        "badge": "",
        "badge_class": ""
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
OVERRIDES = {
    "evaluation of the mcgill-tongji blended education program": {
        "extra_types": ["highlight"],
        "badge": "Award Winner",
        "badge_class": "badge-award"
    },
    "progress on catastrophic health expenditure in china": {
        "extra_types": ["first"],  # equal contribution
    },
    # Add more overrides here as needed. Only use "highlight" for award-winning papers.
}

# ---------------------------------------------------------------------------


def serpapi_request(params):
    """Make a request to SerpAPI and return JSON response."""
    base_url = "https://serpapi.com/search.json"
    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}?{query_string}"

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_from_scholar():
    """Fetch publications from Google Scholar using SerpAPI."""
    api_key = os.environ.get("SERPAPI_KEY", "")
    if not api_key:
        print("ERROR: SERPAPI_KEY environment variable is not set.")
        print("Get a free API key at https://serpapi.com/users/sign_up")
        print("Then add it as a GitHub repository secret named SERPAPI_KEY")
        sys.exit(1)

    print(f"Fetching Google Scholar profile: {SCHOLAR_ID}")

    all_articles = []
    start = 0
    page_size = 100  # SerpAPI returns up to 100 per page

    while True:
        print(f"  Fetching articles starting from index {start}...")
        params = {
            "engine": "google_scholar_author",
            "author_id": SCHOLAR_ID,
            "api_key": api_key,
            "start": start,
            "num": page_size,
            "sort": "pubdate"  # Sort by publication date
        }

        data = serpapi_request(params)
        articles = data.get("articles", [])

        if not articles:
            break

        all_articles.extend(articles)
        print(f"  Got {len(articles)} articles (total so far: {len(all_articles)})")

        # Check if there are more pages
        if len(articles) < page_size:
            break

        start += page_size
        time.sleep(1)  # Be polite

    print(f"\nTotal articles fetched: {len(all_articles)}")

    # Process each article
    publications = []
    for article in all_articles:
        title = article.get("title", "")
        authors = article.get("authors", "")
        year = str(article.get("year", ""))

        # Get citation info (journal, volume, etc.)
        citation = article.get("citation", "")
        # SerpAPI returns citation as a string like "Journal Name, Volume(Issue), Pages, Year"
        journal_str = citation if citation else ""

        # If journal_str doesn't include the year, append it
        if year and year not in journal_str and journal_str:
            journal_str += f" ({year})"
        elif year and not journal_str:
            journal_str = f"({year})"

        # Detect first authorship
        is_first = False
        if authors:
            first_author = authors.split(",")[0].strip()
            if YOUR_LAST_NAME.lower() in first_author.lower():
                is_first = True

        pub_types = []
        if is_first:
            pub_types.append("first")

        # Check for overrides
        badge = ""
        badge_class = ""
        title_lower = title.lower()
        for key, override in OVERRIDES.items():
            if title_lower.startswith(key):
                pub_types.extend(override.get("extra_types", []))
                if "badge" in override:
                    badge = override["badge"]
                if "badge_class" in override:
                    badge_class = override["badge_class"]
                break

        # Get links — separate DOI and Google Scholar link
        doi = ""
        scholar_link = ""
        link = article.get("link", "")
        if "doi.org" in link:
            doi = link
        elif link:
            scholar_link = link  # Google Scholar or publisher link

        # SerpAPI sometimes provides citation_id for direct Scholar link
        citation_id = article.get("citation_id", "")
        if citation_id and not scholar_link:
            scholar_link = f"https://scholar.google.com/citations?view_op=view_citation&hl=en&user={SCHOLAR_ID}&citation_for_view={SCHOLAR_ID}:{citation_id}"

        publications.append({
            "title": title,
            "authors": authors,
            "journal": journal_str,
            "year": year,
            "doi": doi,
            "scholar_link": scholar_link,
            "type": list(set(pub_types)),
            "badge": badge,
            "badge_class": badge_class
        })

        print(f"  Processed: {title[:60]}...")

    return publications


def main():
    print("=" * 60)
    print("Google Scholar Publication Sync (via SerpAPI)")
    print("=" * 60)

    # Fetch from Google Scholar
    scholar_pubs = fetch_from_scholar()
    print(f"\nFetched {len(scholar_pubs)} publications from Google Scholar.")

    # Sort by year descending
    scholar_pubs.sort(key=lambda p: p.get("year", "0"), reverse=True)

    # --- Deduplicate: remove manual entries that now appear on Google Scholar ---
    # This handles the case where a paper was under review (manual) and is now
    # published (auto-fetched). We compare by checking if the first 40 chars of
    # the title match (case-insensitive).
    scholar_titles = set()
    for pub in scholar_pubs:
        scholar_titles.add(pub["title"].lower()[:40])

    filtered_manual = []
    for entry in MANUAL_ENTRIES:
        entry_key = entry["title"].lower()[:40]
        if entry_key in scholar_titles:
            print(f"  Dedup: skipping manual entry '{entry['title'][:50]}...' (now on Google Scholar)")
        else:
            filtered_manual.append(entry)

    print(f"  Manual entries: {len(MANUAL_ENTRIES)} total, {len(filtered_manual)} after dedup")

    result = {
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scholar_id": SCHOLAR_ID,
        "scholar_url": f"https://scholar.google.com/citations?user={SCHOLAR_ID}&hl=en",
        "publications": scholar_pubs,
        "manual_entries": filtered_manual
    }

    # Write JSON
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), OUTPUT_FILE)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {len(scholar_pubs) + len(filtered_manual)} total entries to {OUTPUT_FILE}")
    print(f"  - {len(scholar_pubs)} from Google Scholar")
    print(f"  - {len(filtered_manual)} manual entries")
    print("Done!")


if __name__ == "__main__":
    main()
