import os
import random
import sys
from utils import (
    DATA_PATH, USERS_PATH,
    load_json, save_json
)

# Force UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# New SBERT Cluster Legend:
# Cluster 0: Global Business & Maritime Logistics
# Cluster 1: Energy Markets & Middle East Tensions
# Cluster 2: Local Governance & Political Profiles
# Cluster 3: National Development & Public Policy
# Cluster 4: Technological Regulation & Social Care
# Cluster 5: Iran-Israel Geopolitical Conflict
# Cluster 6: Arts, Humanities & Creative Expression
# Cluster 7: Community Health & Emergency Services

PERSONAS = {
    "The Global Strategist": {
        "description": "Analyzes international relations, energy markets, and geopolitical tensions in the Middle East.",
        "preferred_clusters": ["topic_1", "topic_5"] 
    },
    "The Local Policy Critic": {
        "description": "Focuses on Maltese governance, national infrastructure projects, and legislative reforms.",
        "preferred_clusters": ["topic_2", "topic_3"] 
    },
    "The Tech & Business Leader": {
        "description": "Tracks global trade, maritime logistics, and the regulation of emerging technologies.",
        "preferred_clusters": ["topic_0", "topic_4"] 
    },
    "The Social & Arts Advocate": {
        "description": "Engaged with community health, emergency services, and the creative arts scene.",
        "preferred_clusters": ["topic_6", "topic_7"] 
    }
}

def main():
    articles = load_json(DATA_PATH)
    if not articles:
        print("Data file not found or empty. Run topic modeling first.")
        return

    # Filter out articles without a topic vector
    valid_articles = [a for a in articles if a.get('topic_vector')]
    print(f"Creating simulated users based on {len(valid_articles)} available categorized articles...")

    # Group articles by their dominant cluster to make sampling easier
    articles_by_cluster = {f"topic_{i}": [] for i in range(8)}
    for article in valid_articles:
        vector = article['topic_vector']
        dominant_topic = max(vector, key=vector.get)
        articles_by_cluster[dominant_topic].append(article)

    user_profiles = []

    for name, metadata in PERSONAS.items():
        print(f"Generating profile: {name}")
        
        # Give each user a "reading history" of 15 articles
        history = []
        preferred_clusters = metadata['preferred_clusters']
        
        # 80% of their reading history comes from their preferred clusters
        # 20% is random noise to simulate occasional random clicking
        num_preferred = int(15 * 0.8)
        num_random = 15 - num_preferred

        # Add preferred articles
        for _ in range(num_preferred):
            chosen_cluster = random.choice(preferred_clusters)
            if articles_by_cluster[chosen_cluster]:
                chosen_article = random.choice(articles_by_cluster[chosen_cluster])
                history.append({
                    "link": chosen_article["link"],
                    "title": chosen_article["title"],
                    "dominant_topic": chosen_cluster,
                    "topic_vector": chosen_article["topic_vector"]
                })

        # Add random articles
        all_clusters = list(articles_by_cluster.keys())
        for _ in range(num_random):
            random_cluster = random.choice(all_clusters)
            if articles_by_cluster[random_cluster]:
                chosen_article = random.choice(articles_by_cluster[random_cluster])
                history.append({
                    "link": chosen_article["link"],
                    "title": chosen_article["title"],
                    "dominant_topic": random_cluster,
                    "topic_vector": chosen_article["topic_vector"]
                })

        # Create the profile
        user_profiles.append({
            "id": f"user_{len(user_profiles)+1}",
            "name": name,
            "description": metadata["description"],
            "reading_history": history
        })

    save_json(USERS_PATH, user_profiles)
    print(f"\nSuccessfully generated {len(PERSONAS)} user profiles and saved to {USERS_PATH}")

if __name__ == "__main__":
    main()
