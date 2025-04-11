import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re
import csv
import json
from urllib.parse import urlparse, parse_qs

BASE_URL = "https://www.thegreatcoursesplus.com"
START_PATH = "/allsubjects"
HEADERS = {"User-Agent": "Mozilla/5.0"}

visited_urls = set()
category_links = []
course_links = []
course_data = []

def fetch_ajax_review_info(product_id):
    """Fetch and parse embedded HTML from AJAX course info widget."""
    ajax_url = f"https://api.bazaarvoice.com/data/display/0.2alpha/product/summary?PassKey=e62nfrixo047lx9pgj2w7w6ox&productid={product_id}&contentType=reviews%2Cquestions&reviewDistribution=primaryRating%2Crecommended&rev=0&contentlocale=en_US%2Cen_CA"

    try:
        response = requests.get(ajax_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "reviewSummary" in data.keys():
            num_reviews = data["reviewSummary"]["numReviews"]
            rating = data["reviewSummary"]["primaryRating"]["average"]

            return num_reviews, rating
        return None
    except Exception as e:
        print(f"[Error] Failed to fetch review info: {e}")
        return None

def get_view_all_links(url):
    full_url = urljoin(BASE_URL, url)
    if full_url in visited_urls:
        return
    print(f"[Category] Visiting: {full_url}")
    visited_urls.add(full_url)

    try:
        response = requests.get(full_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", class_="tray__view-all")

        for link in links:
            href = link.get("href")
            if href:
                abs_href = urljoin(BASE_URL, href)
                if abs_href not in category_links:
                    category_links.append(abs_href)
                    get_view_all_links(href)
        time.sleep(1)
    except Exception as e:
        print(f"[Error] Failed to process {full_url}: {e}")

def extract_courses_from_category(url):
    print(f"[Courses] Extracting from: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", class_="item__link")

        for link in links:
            href = link.get("href")
            if href:
                abs_href = urljoin(BASE_URL, href)
                if abs_href not in course_links:
                    course_links.append(abs_href)
        time.sleep(1)
    except Exception as e:
        print(f"[Error] Failed to extract courses from {url}: {e}")

def extract_course_metadata(url):
    print(f"[Metadata] Scraping: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # HTML scrape
        title_tag = soup.find("h1", itemprop="name")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"

        runtime_tags = soup.find_all("span", class_="total-len small")
        total_minutes = sum(int(m.group(1)) for tag in runtime_tags if (m := re.search(r"(\d+)\s*min", tag.get_text(strip=True))))

        # Extract product ID
        product_id_tag = soup.find("div", {"data-bv-product-id": True, "data-bv-show": "reviews"})
        product_id = product_id_tag.get("data-bv-product-id") if product_id_tag else None
        if product_id:
            (num_reviews, rating) = fetch_ajax_review_info(product_id)
        
        professor_tag = soup.find("a", class_="professor-name h2 m-0 n-link")
        professor = professor_tag.get_text(strip=True) if professor_tag else "N/A"

        course_data.append({
            "title": title,
            "url": url,
            "rating": rating,
            "total_runtime_minutes": total_minutes,
            "num_reviews": num_reviews,
            "professor": professor,
            "product_id": product_id
        })
        time.sleep(1)
    except Exception as e:
        print(f"[Error] Failed to scrape metadata from {url}: {e}")

# Phase 1
get_view_all_links(START_PATH)

# Phase 2
for cat_link in category_links:
    extract_courses_from_category(cat_link)

# Phase 3
for course_link in course_links:
    extract_course_metadata(course_link)
    print(course_data)

# Export to CSV
with open("great_courses_metadata.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames = [
    "title", "url", "rating", "total_runtime_minutes",
    "num_reviews", "professor", "product_id"
])
    writer.writeheader()
    writer.writerows(course_data)

print(f"\n✅ Scraped metadata for {len(course_data)} courses. Data saved to 'great_courses_metadata.csv'")