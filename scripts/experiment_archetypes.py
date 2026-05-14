import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import json

from utils import DATA_PATH, load_json
from evaluate_comparison import evaluate_user
from recommend_gmm import build_article_index
from generate_mock_users import generate_users

PLOT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'experiments')
os.makedirs(PLOT_DIR, exist_ok=True)

def main():
    print("Loading data...")
    articles = load_json(DATA_PATH)
    if not articles:
        return

    # Use standard K=8 for this comparison
    print("Generating users for archetype analysis...")
    users = generate_users(articles, num_clusters=8, num_users=500)
    art_index = build_article_index(articles)

    # Group metrics by archetype
    archetype_data = {}

    print("Evaluating...")
    for user in users:
        arch = user['archetype']
        if arch not in archetype_data:
            archetype_data[arch] = {'km_rel': [], 'gmm_rel': [], 'km_cov': [], 'gmm_cov': []}
        
        km_res = evaluate_user(user, articles, 'kmeans', top_n=10, diversity=0.0, article_index=art_index)
        gmm_res = evaluate_user(user, articles, 'gmm', top_n=10, diversity=0.0, article_index=art_index)
        
        if km_res and gmm_res:
            archetype_data[arch]['km_rel'].append(km_res['avg_relevance'])
            archetype_data[arch]['gmm_rel'].append(gmm_res['avg_relevance'])
            archetype_data[arch]['km_cov'].append(km_res['coverage'])
            archetype_data[arch]['gmm_cov'].append(gmm_res['coverage'])

    # Aggregate means
    labels = sorted(archetype_data.keys())
    km_rel_means = [np.mean(archetype_data[l]['km_rel']) for l in labels]
    gmm_rel_means = [np.mean(archetype_data[l]['gmm_rel']) for l in labels]
    
    km_cov_means = [np.mean(archetype_data[l]['km_cov']) for l in labels]
    gmm_cov_means = [np.mean(archetype_data[l]['gmm_cov']) for l in labels]

    # Plot 1: Relevance by Archetype
    plt.figure(figsize=(10, 6))
    x = np.arange(len(labels))
    width = 0.35
    
    plt.bar(x - width/2, km_rel_means, width, label='K-Means', color='#3498db')
    plt.bar(x + width/2, gmm_rel_means, width, label='GMM', color='#e74c3c')
    
    plt.ylabel('Average Relevance Score')
    plt.title('Relevance Performance by User Archetype (Top-10)')
    plt.xticks(x, labels, rotation=45, ha='right')
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, 'archetype_relevance.png'), dpi=300)
    print("Saved archetype_relevance.png")

    # Plot 2: Coverage by Archetype
    plt.figure(figsize=(10, 6))
    plt.bar(x - width/2, km_cov_means, width, label='K-Means', color='#3498db')
    plt.bar(x + width/2, gmm_cov_means, width, label='GMM', color='#e74c3c')
    
    plt.ylabel('Topic Coverage (Distinct Clusters)')
    plt.title('Topic Coverage by User Archetype (Top-10)')
    plt.xticks(x, labels, rotation=45, ha='right')
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, 'archetype_coverage.png'), dpi=300)
    print("Saved archetype_coverage.png")

if __name__ == "__main__":
    main()
