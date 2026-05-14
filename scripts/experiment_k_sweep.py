import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import copy

from utils import DATA_PATH, load_json
from run_topic_modeling import run_kmeans, run_gmm
from generate_mock_users import generate_users
from evaluate_comparison import evaluate_user
from recommend_gmm import build_article_index

PLOT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'experiments')
os.makedirs(PLOT_DIR, exist_ok=True)

def plot_metric(sweep_values, kmeans_vals, gmm_vals, xlabel, ylabel, title, filename):
    plt.figure(figsize=(8, 5))
    plt.plot(sweep_values, kmeans_vals, marker='o', linestyle='-', label='SBERT + KMeans', color='b')
    plt.plot(sweep_values, gmm_vals, marker='s', linestyle='-', label='SBERT + GMM', color='r')
    
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    
    filepath = os.path.join(PLOT_DIR, filename)
    plt.savefig(filepath, dpi=300)
    plt.close()
    print(f"Saved plot: {filepath}")

def main():
    print("Loading data...")
    # Load original articles. We will manipulate this in memory.
    original_articles = load_json(DATA_PATH)
    if not original_articles:
        print("Data missing. Exiting.")
        return

    k_values = [5, 8, 15, 30, 50]
    
    results = {
        'kmeans': {'relevance': [], 'ils': [], 'coverage': [], 'hit_rate': []},
        'gmm':    {'relevance': [], 'ils': [], 'coverage': [], 'hit_rate': []}
    }

    # Evaluate Top-10
    TOP_N = 10
    DIVERSITY = 0.0
    NUM_EVAL_USERS = 200  # Generate 200 dynamic users per K to evaluate

    for k in k_values:
        print(f"\n=======================================================")
        print(f"  Running Experiment for K = {k}")
        print(f"=======================================================")
        
        # Deep copy to avoid progressive mutation side-effects, though overwriting keys is fine
        articles = copy.deepcopy(original_articles)
        
        # CLEAR ALL old vectors so invalid articles don't retain size-8 vectors from cache
        for a in articles:
            a.pop('topic_vector', None)
            a.pop('gmm_topic_vector', None)
        
        # 1. Re-cluster in memory
        articles = run_kmeans(articles, num_clusters=k)
        articles = run_gmm(articles, num_clusters=k, temperature=35.0)
        
        # 2. Build index
        art_index = build_article_index(articles)
        
        # 3. Dynamically generate mock users who prefer these new K clusters
        print(f"\nGenerating {NUM_EVAL_USERS} dynamic mock users for K={k}...")
        users = generate_users(articles, num_clusters=k, num_users=NUM_EVAL_USERS)
        
        km_metrics = {'rel': [], 'ils': [], 'cov': [], 'hr': []}
        gmm_metrics = {'rel': [], 'ils': [], 'cov': [], 'hr': []}

        # 4. Evaluate each user
        print(f"Evaluating recommendations (Top-{TOP_N}) for both models...")
        for user in users:
            km_res = evaluate_user(user, articles, 'kmeans', TOP_N, DIVERSITY, article_index=art_index)
            gmm_res = evaluate_user(user, articles, 'gmm', TOP_N, DIVERSITY, article_index=art_index)
            
            if km_res:
                km_metrics['rel'].append(km_res['avg_relevance'])
                km_metrics['ils'].append(km_res['ils'])
                km_metrics['cov'].append(km_res['coverage'])
                km_metrics['hr'].append(km_res['hit_rate'])
                
            if gmm_res:
                gmm_metrics['rel'].append(gmm_res['avg_relevance'])
                gmm_metrics['ils'].append(gmm_res['ils'])
                gmm_metrics['cov'].append(gmm_res['coverage'])
                gmm_metrics['hr'].append(gmm_res['hit_rate'])

        # Aggregate
        results['kmeans']['relevance'].append(np.mean(km_metrics['rel']))
        results['kmeans']['ils'].append(np.mean(km_metrics['ils']))
        results['kmeans']['coverage'].append(np.mean(km_metrics['cov']))
        results['kmeans']['hit_rate'].append(np.mean(km_metrics['hr']))

        results['gmm']['relevance'].append(np.mean(gmm_metrics['rel']))
        results['gmm']['ils'].append(np.mean(gmm_metrics['ils']))
        results['gmm']['coverage'].append(np.mean(gmm_metrics['cov']))
        results['gmm']['hit_rate'].append(np.mean(gmm_metrics['hr']))
        
        print(f"  [KMeans] Relevance: {results['kmeans']['relevance'][-1]:.4f} | Coverage: {results['kmeans']['coverage'][-1]:.2f}")
        print(f"  [GMM]    Relevance: {results['gmm']['relevance'][-1]:.4f} | Coverage: {results['gmm']['coverage'][-1]:.2f}")

    print("\nGenerating charts...")
    plot_metric(k_values, results['kmeans']['relevance'], results['gmm']['relevance'], 
                'Number of Clusters (K)', 'Average Relevance Score', 
                'Relevance vs Number of Clusters (K)', 'k_vs_relevance.png')

    plot_metric(k_values, results['kmeans']['coverage'], results['gmm']['coverage'], 
                'Number of Clusters (K)', 'Topic Coverage (Count)', 
                'Topic Coverage vs Number of Clusters (K)', 'k_vs_coverage.png')

    plot_metric(k_values, results['kmeans']['ils'], results['gmm']['ils'], 
                'Number of Clusters (K)', 'Intra-List Similarity (ILS)', 
                'Filter Bubble Strength (ILS) vs Number of Clusters (K)', 'k_vs_ils.png')
                
    plot_metric(k_values, results['kmeans']['hit_rate'], results['gmm']['hit_rate'], 
                'Number of Clusters (K)', 'Hit Rate (Dominant Topic Match)', 
                'Hit Rate vs Number of Clusters (K)', 'k_vs_hit_rate.png')

    print("\nExperiment complete. Data files were not modified.")

if __name__ == '__main__':
    main()
