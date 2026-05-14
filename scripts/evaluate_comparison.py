"""
evaluate_comparison.py
----------------------
Side-by-side evaluation of the two recommendation pipelines:

  Method A: SBERT + KMeans   (uses article['topic_vector'])
  Method B: SBERT + GMM      (uses article['gmm_topic_vector'])

Evaluation metrics computed for each user × method combination
--------------------------------------------------------------
1. Avg Relevance Score   — mean cosine similarity of Top-N results to the user
                           profile vector (higher = more relevant)
2. Intra-List Similarity — mean pairwise cosine similarity within the Top-N list
                           (higher = more filter-bubble-like; lower = more diverse)
3. Topic Coverage        — number of distinct dominant clusters in Top-N
                           (higher = more topically diverse)
4. Hit Rate              — % of Top-N whose dominant cluster matches the user's
                           single strongest cluster (higher = more on-target)

Run:
    python scripts/evaluate_comparison.py
"""

import os
import sys
import argparse
import numpy as np
from itertools import combinations

from utils import DATA_PATH, USERS_PATH, EVAL_OUTPUT, load_json

# Import both recommendation functions
from recommend     import recommend_articles,     calculate_user_profile_vector, get_vector_array
from recommend_gmm import recommend_articles_gmm, calculate_user_gmm_profile,   get_gmm_vector, build_article_index

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def intra_list_similarity(recs, vector_fn):
    """Mean cosine similarity between all pairs in the Top-N list."""
    if len(recs) < 2:
        return 0.0
    vecs = [vector_fn(article) for _, _, article in recs]
    sims = []
    for va, vb in combinations(vecs, 2):
        na, nb = np.linalg.norm(va), np.linalg.norm(vb)
        if na == 0 or nb == 0:
            continue
        sims.append(float(np.dot(va, vb) / (na * nb)))
    return float(np.mean(sims)) if sims else 0.0


def topic_coverage(recs, vector_fn):
    """Count of distinct dominant clusters in the Top-N list (uses whichever vec field is present)."""
    dominant_clusters = set()
    for _, _, article in recs:
        vec_dict = article.get('topic_vector') or article.get('gmm_topic_vector') or {}
        if vec_dict:
            dominant_clusters.add(max(vec_dict, key=vec_dict.get))
    return len(dominant_clusters)


def _topic_coverage_by_key(recs, vec_key):
    """Count of distinct dominant clusters using a specific vec_key field."""
    dominant_clusters = set()
    for _, _, article in recs:
        vec_dict = article.get(vec_key, {})
        if vec_dict:
            dominant_clusters.add(max(vec_dict, key=vec_dict.get))
    return len(dominant_clusters)


def hit_rate(recs, user_top_cluster, vector_fn):
    """Fraction of Top-N whose dominant cluster == user's top preferred cluster."""
    hits = 0
    for _, _, article in recs:
        vec_dict = article.get('topic_vector') or article.get('gmm_topic_vector') or {}
        if vec_dict:
            if max(vec_dict, key=vec_dict.get) == f"topic_{user_top_cluster}":
                hits += 1
    return hits / len(recs) if recs else 0.0


def _hit_rate_by_key(recs, user_top_cluster, vec_key):
    """Fraction of Top-N matching user's top cluster, using a specific vec_key."""
    hits = 0
    for _, _, article in recs:
        vec_dict = article.get(vec_key, {})
        if vec_dict:
            if max(vec_dict, key=vec_dict.get) == f"topic_{user_top_cluster}":
                hits += 1
    return hits / len(recs) if recs else 0.0


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def evaluate_user(user, all_articles, method, top_n, diversity, article_index=None):
    """Run one method on one user and return a metrics dict."""
    if method == 'kmeans':
        recs, user_vec = recommend_articles(
            user, all_articles, num_recommendations=top_n, diversity_score=diversity
        )
        vec_fn  = lambda art: get_vector_array(art.get('topic_vector', {}))
        vec_key = 'topic_vector'
    else:
        recs, user_vec = recommend_articles_gmm(
            user, all_articles, num_recommendations=top_n, diversity_score=diversity,
            article_index=article_index
        )
        vec_fn  = lambda art: get_gmm_vector(art)
        vec_key = 'gmm_topic_vector'

    if not recs:
        return None

    avg_relevance = float(np.mean([sim for _, sim, _ in recs]))
    ils           = intra_list_similarity(recs, vec_fn)
    # Pass correct vec_key so coverage/hit_rate use the right field
    coverage      = _topic_coverage_by_key(recs, vec_key)
    user_top      = int(np.argmax(user_vec))
    hr            = _hit_rate_by_key(recs, user_top, vec_key)

    return {
        'method':        'KMeans' if method == 'kmeans' else 'GMM',
        'avg_relevance': avg_relevance,
        'ils':           ils,
        'coverage':      coverage,
        'hit_rate':      hr,
        'user_top':      user_top,
        'recs':          recs,
        'vec_key':       vec_key,
    }


def format_table(rows, headers):
    """Render a left-aligned plain-text table."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    sep  = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'
    hdr  = '|' + '|'.join(f' {h:<{col_widths[i]}} ' for i, h in enumerate(headers)) + '|'
    lines = [sep, hdr, sep]
    for row in rows:
        lines.append('|' + '|'.join(f' {str(c):<{col_widths[i]}} ' for i, c in enumerate(row)) + '|')
    lines.append(sep)
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Evaluate recommendation systems side-by-side.")
    parser.add_argument("--top-n", type=int, default=5, help="Number of recommendations to evaluate.")
    parser.add_argument("--diversity", type=float, default=0.0, help="Diversity score to inject into recommendations.")
    args = parser.parse_args()

    all_articles = load_json(DATA_PATH)
    users        = load_json(USERS_PATH)

    if not all_articles or not users:
        print("Required data files not found. Run fetch_news, topic_modeling, and simulate_users first.")
        return

    kmeans_count = sum(1 for a in all_articles if a.get('topic_vector'))
    gmm_count    = sum(1 for a in all_articles if a.get('gmm_topic_vector'))

    print(f"Articles with KMeans vectors : {kmeans_count}")
    print(f"Articles with GMM vectors    : {gmm_count}")

    if gmm_count == 0:
        print("\nERROR: No GMM topic vectors found.")
        print("  Run:  python scripts/run_topic_modeling.py --method gmm")
        return

    # Build link → article index once, reused by all GMM evaluations
    art_index = build_article_index(all_articles)

    # -----------------------------------------------------------------------
    # Per-user comparison table
    # -----------------------------------------------------------------------
    output_lines = []
    summary_rows = []   # for aggregate table

    for user in users:
        km_res  = evaluate_user(user, all_articles, 'kmeans', args.top_n, args.diversity, article_index=art_index)
        gmm_res = evaluate_user(user, all_articles, 'gmm',    args.top_n, args.diversity, article_index=art_index)

        if not km_res or not gmm_res:
            continue

        block  = []
        block.append(f"\n{'='*70}")
        block.append(f"  USER : {user['name']}")
        block.append(f"  DESC : {user['description']}")
        block.append(f"{'='*70}")

        # Metrics side-by-side
        headers = ['Metric', 'SBERT + KMeans', 'SBERT + GMM', 'Δ (GMM − KMeans)']
        rows = [
            ['Avg Relevance Score',
             f"{km_res['avg_relevance']:.4f}",
             f"{gmm_res['avg_relevance']:.4f}",
             f"{gmm_res['avg_relevance'] - km_res['avg_relevance']:+.4f}"],
            ['Intra-List Similarity (ILS)',
             f"{km_res['ils']:.4f}",
             f"{gmm_res['ils']:.4f}",
             f"{gmm_res['ils'] - km_res['ils']:+.4f}"],
            ['Topic Coverage (of 8)',
             str(km_res['coverage']),
             str(gmm_res['coverage']),
             f"{gmm_res['coverage'] - km_res['coverage']:+d}"],
            ['Hit Rate (top cluster)',
             f"{km_res['hit_rate']:.2%}",
             f"{gmm_res['hit_rate']:.2%}",
             ''],
        ]
        block.append(format_table(rows, headers))

        # KMeans Top-N
        block.append(f"\n  [SBERT + KMeans] Top-{args.top_n} recommendations:")
        for rank, (score, sim, art) in enumerate(km_res['recs'], 1):
            vec_dict = art.get('topic_vector', {})
            dom = max(vec_dict, key=vec_dict.get).replace('topic_', 'Cluster ') if vec_dict else 'N/A'
            block.append(f"    [{rank}] sim={sim:.3f} | {art['title'][:60]}... [{dom}]")

        # GMM Top-N
        block.append(f"\n  [SBERT + GMM]    Top-{args.top_n} recommendations:")
        for rank, (score, sim, art) in enumerate(gmm_res['recs'], 1):
            vec_dict = art.get('gmm_topic_vector', {})
            dom = max(vec_dict, key=vec_dict.get).replace('topic_', 'Cluster ') if vec_dict else 'N/A'
            block.append(f"    [{rank}] sim={sim:.3f} | {art['title'][:60]}... [{dom}]")

        output_lines.extend(block)

        # Collect for aggregate summary
        summary_rows.append([
            user['name'][:24],
            f"{km_res['avg_relevance']:.4f}",
            f"{gmm_res['avg_relevance']:.4f}",
            f"{km_res['ils']:.4f}",
            f"{gmm_res['ils']:.4f}",
            str(km_res['coverage']),
            str(gmm_res['coverage']),
            f"{km_res['hit_rate']:.2%}",
            f"{gmm_res['hit_rate']:.2%}",
        ])

    # -----------------------------------------------------------------------
    # Aggregate summary
    # -----------------------------------------------------------------------
    agg_headers = [
        'User', 'KM-Rel', 'GMM-Rel',
        'KM-ILS', 'GMM-ILS',
        'KM-Cov', 'GMM-Cov',
        'KM-HR', 'GMM-HR',
    ]

    summary_block = [
        '\n' + '='*70,
        '  AGGREGATE COMPARISON SUMMARY',
        '  Metric definitions:',
        '    Rel  = Avg Relevance Score  (higher = more on-target)',
        '    ILS  = Intra-List Similarity (higher = stronger filter bubble)',
        '    Cov  = Topic Coverage out of 8 clusters (higher = more diverse)',
        '    HR   = Hit Rate on user top cluster (higher = more personalised)',
        '='*70,
        format_table(summary_rows, agg_headers),
    ]
    output_lines.extend(summary_block)

    # -----------------------------------------------------------------------
    # Print and save
    # -----------------------------------------------------------------------
    full_output = '\n'.join(output_lines)
    print(full_output)

    with open(EVAL_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(full_output)
    print(f"\nEvaluation report saved to: {EVAL_OUTPUT}")


if __name__ == "__main__":
    main()
