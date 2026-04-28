import os
import sys
import numpy as np
from utils import (
    DATA_PATH, USERS_PATH,
    load_json
)

# Force UTF-8 for Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def get_vector_array(topic_vector_dict):
    """ Converts a dictionary vector {'topic_0': 1.0, ...} to a numpy array ordered by topic id """
    # SBERT has 8 clusters (0 to 7)
    arr = [0.0] * 8
    if not topic_vector_dict:
        return np.array(arr)
    for k, v in topic_vector_dict.items():
        try:
            # Assuming format 'topic_X'
            idx = int(k.split('_')[1])
            arr[idx] = float(v)
        except:
            pass
    return np.array(arr)

def cosine_similarity(vec_a, vec_b):
    """ Mathematical similarity between two vectors (-1 to 1) """
    if np.linalg.norm(vec_a) == 0 or np.linalg.norm(vec_b) == 0:
        return 0.0
    return np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))

def calculate_user_profile_vector(reading_history):
    """ Average all the topic vectors of articles the user has read. """
    if not reading_history:
        return np.zeros(8)
        
    sum_vector = np.zeros(8)
    for article in reading_history:
        vec = get_vector_array(article.get('topic_vector'))
        sum_vector += vec
        
    # Average the vector
    avg_vector = sum_vector / len(reading_history)
    return avg_vector

def recommend_articles(user, all_articles, num_recommendations=5, diversity_score=0.0):
    """
    Core Recommendation Engine.
    - diversity_score = 0.0: Perfect mathematical similarity matching
    - diversity_score = 1.0: Introduces high noise for algorithmic exploration
    """
    user_vector = calculate_user_profile_vector(user.get('reading_history', []))
    
    # Extract links the user has already read so we don't recommend them again
    read_links = {a['link'] for a in user.get('reading_history', [])}
    
    scored_articles = []
    
    for article in all_articles:
        if not article.get('topic_vector'):
            continue # Skip unanalyzed articles
            
        if article['link'] in read_links:
            continue # User already read it
            
        article_vector = get_vector_array(article['topic_vector'])
        
        # 1. Base Score: How similar is the article to the user's past reading?
        similarity = cosine_similarity(user_vector, article_vector)
        
        # 2. Diversity Injection 
        noise = np.random.uniform(0, 1.0)
        final_score = ((1.0 - diversity_score) * similarity) + (diversity_score * noise)
        
        scored_articles.append((final_score, similarity, article))
        
    # Sort descending by the final modified score
    scored_articles.sort(key=lambda x: x[0], reverse=True)
    
    return scored_articles[:num_recommendations], user_vector

def main():
    all_articles = load_json(DATA_PATH)
    users = load_json(USERS_PATH)

    if not all_articles or not users:
        print("Required data files not found or empty. Run previous scripts first.")
        return

    # Let's test the engine on the first user ("The Global Forecaster")
    test_user = users[0]
    print(f"\n======== Executing Engine Validation ========")
    print(f"User Subject: {test_user['name']} | Profile: {test_user['description']}")
    
    # TEST 1: High Relevance (0% Diversity)
    print("\n--- TEST 1: HIGH RELEVANCE CALIBRATION (Diversity = 0.0) ---")
    recommendations, user_vector = recommend_articles(test_user, all_articles, num_recommendations=3, diversity_score=0.0)
    
    # Show user's mathematical preference
    top_cluster = np.argmax(user_vector)
    print(f"User's primary representation alignment: Cluster {top_cluster}")
    
    for rank, (score, sim, article) in enumerate(recommendations, 1):
        dom_topic = max(article['topic_vector'], key=article['topic_vector'].get).replace('topic_', 'Cluster ')
        print(f"[{rank}] (Sim: {sim:.2f}) {article['title'][:70]}... [{dom_topic}]")

    # TEST 2: Exploration Injection (80% Diversity)
    print("\n--- TEST 2: NOISE INJECTION EXPLORATION (Diversity = 0.8) ---")
    recommendations, _ = recommend_articles(test_user, all_articles, num_recommendations=3, diversity_score=0.8)
    
    for rank, (score, sim, article) in enumerate(recommendations, 1):
        dom_topic = max(article['topic_vector'], key=article['topic_vector'].get).replace('topic_', 'Cluster ')
        print(f"[{rank}] (Final: {score:.2f} | Sim: {sim:.2f}) {article['title'][:70]}... [{dom_topic}]")
        
    print("\nRecommendation Engine calibration tests completed.")

if __name__ == "__main__":
    main()
