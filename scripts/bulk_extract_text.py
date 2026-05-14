import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from utils import (
    DATA_PATH, fetch_full_text,
    load_json, save_json
)


def process_article(article):
    if not article.get('full_text'):
        article['full_text'] = fetch_full_text(article['link'])
    return article

def main():
    articles = load_json(DATA_PATH)
    if not articles:
        print(f"Error: {DATA_PATH} not found or empty.")
        return

    # Filter articles that need fetching
    to_fetch = [a for a in articles if not a.get('full_text')]
    already_done = [a for a in articles if a.get('full_text')]
    
    print(f"Total articles: {len(articles)}")
    print(f"Already extracted: {len(already_done)}")
    print(f"To extract: {len(to_fetch)}")

    if not to_fetch:
        print("Nothing to extract.")
        return

    updated_articles = []
    # Using 10 threads to avoid overwhelming the sites while keeping it fast
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_article = {executor.submit(process_article, article): article for article in to_fetch}
        
        # tqdm for progress bar
        for future in tqdm(as_completed(future_to_article), total=len(to_fetch), desc="Extracting text"):
            updated_articles.append(future.result())

    # Combine back
    final_dataset = already_done + updated_articles
    
    save_json(DATA_PATH, final_dataset)
    print(f"\nSuccessfully updated {DATA_PATH}")
    print(f"Total entries with text: {len([a for a in final_dataset if a.get('full_text')])}")

if __name__ == "__main__":
    main()
