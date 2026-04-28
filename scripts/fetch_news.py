import requests
import re
import os
from datetime import datetime
from utils import (
    DATA_PATH, HEADERS, clean_html, fetch_full_text,
    load_json, save_json
)

"""
Robust news scraper using Regex fallbacks for messy news feeds.
Targeting 100+ articles with full description, full text and pubDate fields.
Supports incremental fetching (only adds new articles).
"""

FEEDS = {
    # --------------------------------------------------------------------------
    # LOCAL MALTA NEWS (Core Base)
    # --------------------------------------------------------------------------
    "TVM News": "https://tvmnews.mt/en/feed/",
    "Times of Malta": "https://timesofmalta.com/rss",
    "Malta Independent": "https://www.independent.com.mt/rss",
    "Newsbook (EN)": "https://newsbook.com.mt/en/feed/",
    "Lovin Malta": "https://lovinmalta.com/feed/",
    "MaltaToday": "https://www.maltatoday.com.mt/rss/",
    "The Shift News": "https://theshiftnews.com/feed/",

    # --------------------------------------------------------------------------
    # GLOBAL GEOPOLITICS & WORLD NEWS
    # --------------------------------------------------------------------------
    "BBC World News": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "Reuters Top": "https://rss.app/feeds/XbYyA0fEbdS7sP6X.xml", # Kept if valid, or we could use alternatives
    "The Guardian World": "https://www.theguardian.com/world/rss",
    "CNN Top Stories": "http://rss.cnn.com/rss/cnn_topstories.rss",
    "NPR World": "https://feeds.npr.org/1004/rss.xml",
    "NYT World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "EuroNews": "https://www.euronews.com/rss",
    "UN News": "https://news.un.org/feed/subscribe/en/news/all/rss.xml",

    # --------------------------------------------------------------------------
    # POLITICS & IDEOLOGICAL COMMENTARY
    # --------------------------------------------------------------------------
    "FOX News Politics": "https://feeds.foxnews.com/foxnews/politics",
    "MSNBC Top": "https://www.msnbc.com/feeds/latest",
    "Breitbart": "https://www.breitbart.com/feed/",
    "Jacobin (Left)": "https://jacobin.com/feed",
    "National Review (Right)": "https://www.nationalreview.com/feed/",
    "Politico": "https://rss.politico.com/politics-news.xml",

    # --------------------------------------------------------------------------
    # FINANCE, ECONOMICS & BUSINESS
    # --------------------------------------------------------------------------
    "BBC Business": "http://feeds.bbci.co.uk/news/business/rss.xml",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "CNBC Top News": "https://www.cnbc.com/id/10000311/device/rss/rss.html",
    "BusinessNow Malta": "https://businessnow.mt/feed/",
    "Economist Business": "https://www.economist.com/business/rss.xml",

    # --------------------------------------------------------------------------
    # SCIENCE, HEALTH & ENVIRONMENT
    # --------------------------------------------------------------------------
    "ScienceDaily": "https://www.sciencedaily.com/rss/all.xml",
    "Nature News": "https://www.nature.com/nature.rss",
    "Inside Climate News": "https://insideclimatenews.org/feed/",
    "Grist": "https://grist.org/feed/",
    "Medical News Today": "https://www.medicalnewstoday.com/feed/rss",
    "NASA Breaking News": "https://www.nasa.gov/news-release/feed/",
    "NYT Science": "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
    "NYT Health": "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
    "BBC Health": "http://feeds.bbci.co.uk/news/health/rss.xml",

    # --------------------------------------------------------------------------
    # TECHNOLOGY & INNOVATION
    # --------------------------------------------------------------------------
    "BBC Tech": "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "Wired Tech": "https://www.wired.com/feed/rss",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",

    # --------------------------------------------------------------------------
    # SPORTS & ENTERTAINMENT (For Diverse Injections)
    # --------------------------------------------------------------------------
    "Sky Sports Football": "https://www.skysports.com/rss/12040",
    "BBC Sports": "http://feeds.bbci.co.uk/sport/rss.xml?edition=uk",
    "ESPN Top Topics": "https://www.espn.com/espn/rss/news",
    "IGN Video Games": "https://feeds.feedburner.com/ign/news",
    "Variety Entertainment": "https://variety.com/feed/",
    "BBC Entertainment": "http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    "E! Online": "https://www.eonline.com/syndication/feeds/rssfeeds/topstories.xml",
    "Hollywood Reporter": "https://www.hollywoodreporter.com/c/news/feed/",
    "Rolling Stone": "https://www.rollingstone.com/feed/",
    "NYT Sports": "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",
    "Bleacher Report": "https://bleacherreport.com/articles/feed",
}

def extract_tag(item_str, tag_name):
    """Regex based tag extraction to handle CDATA and namespaces."""
    # Look for <tag>...</tag> or <namespace:tag>...</namespace:tag>
    pattern = rf'<(?:[\w-]+:)?{tag_name}(?:\s+[^>]*?)?>(.*?)</(?:[\w-]+:)?{tag_name}>'
    match = re.search(pattern, item_str, re.DOTALL | re.IGNORECASE)
    if match:
        content = match.group(1)
        # Remove CDATA wrapper if present
        content = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', content, flags=re.DOTALL)
        return content.strip()
    return ""

def fetch_feed(name, url, existing_links):
    print(f"Fetching news from {name}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        content = response.text
        # Split by <item> or <entry>
        items_raw = re.split(r'<(?:item|entry)(?:\s+[^>]*?)?>', content, flags=re.IGNORECASE)[1:]
        
        articles = []
        for item_str in items_raw:
            item_str = re.split(r'</(?:item|entry)>', item_str, flags=re.IGNORECASE)[0]
            
            link = extract_tag(item_str, 'link')
            # Handle <link href="..."/> style
            if not link:
                link_match = re.search(r'href=["\'](.*?)["\']', item_str)
                if link_match:
                    link = link_match.group(1)
            
            # Use link as unique ID
            if link in existing_links:
                continue
                
            title = clean_html(extract_tag(item_str, 'title'))
            description = clean_html(extract_tag(item_str, 'description') or extract_tag(item_str, 'summary') or extract_tag(item_str, 'content'))
            pubDate = extract_tag(item_str, 'pubDate') or extract_tag(item_str, 'published') or extract_tag(item_str, 'updated') or extract_tag(item_str, 'date')
            category = clean_html(extract_tag(item_str, 'category') or "General")

            if title:
                articles.append({
                    "source": name,
                    "title": title,
                    "link": link,
                    "description": description,
                    "pubDate": pubDate,
                    "category": category,
                    "fetched_at": datetime.now().isoformat(),
                    "full_text": "" # To be filled if needed
                })
        
        print(f"  Found {len(articles)} new articles from {name}.")
        return articles
    except Exception as e:
        print(f"Error fetching {name}: {e}")
        return []

def main():
    all_articles = load_json(DATA_PATH)
    existing_links = {a['link'] for a in all_articles if 'link' in a}
    print(f"Loaded {len(all_articles)} existing articles.")

    new_count = 0
    for name, url in FEEDS.items():
        articles = fetch_feed(name, url, existing_links)
        if articles:
            print(f"    Sample: {articles[0]['title'][:50]}...")
            all_articles.extend(articles)
            new_count += len(articles)
    
    if new_count == 0:
        print("\nNo new articles found.")
        return

    print(f"\nTotal articles now: {len(all_articles)} (Added {new_count} new)")
    
    os.makedirs('data', exist_ok=True)
    save_json(DATA_PATH, all_articles)
    print(f"Saved to {DATA_PATH}")
    
    # Fetch full text for the newest 10 articles as a demo
    print("\nFetching full text for a sample of new articles...")
    for article in all_articles[-10:]:
        if not article.get('full_text'):
            print(f"  Fetching: {article['title'][:30]}...")
            article['full_text'] = fetch_full_text(article['link'])
    
    # Re-save with full text
    save_json(DATA_PATH, all_articles)

if __name__ == "__main__":
    main()
