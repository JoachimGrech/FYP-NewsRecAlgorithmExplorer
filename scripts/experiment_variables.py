import os
import sys
import numpy as np
import matplotlib.pyplot as plt

from utils import DATA_PATH, USERS_PATH, load_json
from recommend_gmm import build_article_index

# We can import the evaluate_user function from our existing script
from evaluate_comparison import evaluate_user

# Ensure data directory exists for plots
PLOT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'experiments')
os.makedirs(PLOT_DIR, exist_ok=True)

def run_experiment(all_articles, users, art_index, sweep_var, sweep_values, fixed_kwargs):
    """
    Runs an experiment sweeping over `sweep_var` for the given `sweep_values`.
    `fixed_kwargs` contains the other fixed arguments (e.g. top_n=10, diversity=0.0).
    Returns a dictionary of aggregated metrics for KMeans and GMM.
    """
    results = {
        'kmeans': {'relevance': [], 'ils': [], 'coverage': [], 'hit_rate': []},
        'gmm':    {'relevance': [], 'ils': [], 'coverage': [], 'hit_rate': []}
    }

    for val in sweep_values:
        kwargs = fixed_kwargs.copy()
        kwargs[sweep_var] = val
        
        # Accumulators for this specific value
        km_metrics = {'rel': [], 'ils': [], 'cov': [], 'hr': []}
        gmm_metrics = {'rel': [], 'ils': [], 'cov': [], 'hr': []}

        for user in users:
            km_res = evaluate_user(user, all_articles, 'kmeans', kwargs['top_n'], kwargs['diversity'], article_index=art_index)
            gmm_res = evaluate_user(user, all_articles, 'gmm', kwargs['top_n'], kwargs['diversity'], article_index=art_index)
            
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

        # Average across all users for this sweep value
        results['kmeans']['relevance'].append(np.mean(km_metrics['rel']))
        results['kmeans']['ils'].append(np.mean(km_metrics['ils']))
        results['kmeans']['coverage'].append(np.mean(km_metrics['cov']))
        results['kmeans']['hit_rate'].append(np.mean(km_metrics['hr']))

        results['gmm']['relevance'].append(np.mean(gmm_metrics['rel']))
        results['gmm']['ils'].append(np.mean(gmm_metrics['ils']))
        results['gmm']['coverage'].append(np.mean(gmm_metrics['cov']))
        results['gmm']['hit_rate'].append(np.mean(gmm_metrics['hr']))

    return results

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
    all_articles = load_json(DATA_PATH)
    users = load_json(USERS_PATH)
    
    if not all_articles or not users:
        print("Data missing. Exiting.")
        return

    art_index = build_article_index(all_articles)

    # ---------------------------------------------------------
    # Experiment 1: Sweep Top-N
    # ---------------------------------------------------------
    print("\nRunning Experiment 1: Sweeping Top-N (5 to 25)")
    top_n_values = [5, 10, 15, 20, 25]
    res_top_n = run_experiment(all_articles, users, art_index, sweep_var='top_n', sweep_values=top_n_values, fixed_kwargs={'diversity': 0.0})
    
    plot_metric(top_n_values, res_top_n['kmeans']['relevance'], res_top_n['gmm']['relevance'], 
                'Top-N Recommended Articles', 'Average Relevance Score', 
                'Relevance vs Top-N List Size', 'top_n_vs_relevance.png')

    plot_metric(top_n_values, res_top_n['kmeans']['coverage'], res_top_n['gmm']['coverage'], 
                'Top-N Recommended Articles', 'Topic Coverage (Count)', 
                'Topic Coverage vs Top-N List Size', 'top_n_vs_coverage.png')

    # ---------------------------------------------------------
    # Experiment 2: Sweep Diversity Injection
    # ---------------------------------------------------------
    print("\nRunning Experiment 2: Sweeping Diversity Injection (0.0 to 0.4)")
    diversity_values = [0.0, 0.1, 0.2, 0.3, 0.4]
    res_div = run_experiment(all_articles, users, art_index, sweep_var='diversity', sweep_values=diversity_values, fixed_kwargs={'top_n': 10})

    plot_metric(diversity_values, res_div['kmeans']['relevance'], res_div['gmm']['relevance'], 
                'Diversity Score (Noise Injection)', 'Average Relevance Score', 
                'Relevance vs Diversity Injection (Top-10)', 'diversity_vs_relevance.png')

    plot_metric(diversity_values, res_div['kmeans']['ils'], res_div['gmm']['ils'], 
                'Diversity Score (Noise Injection)', 'Intra-List Similarity (ILS)', 
                'Filter Bubble Strength (ILS) vs Diversity Injection (Top-10)', 'diversity_vs_ils.png')

    print("\nExperiments complete. Visualisations saved to data/experiments/")

if __name__ == '__main__':
    main()
