import argparse
import json
import os
import sys
import numpy as np
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.feature_extraction.text import TfidfVectorizer
from utils import (
    DATA_PATH, TOPICS_OUTPUT_SBERT, TOPICS_OUTPUT_GMM,
    LOCAL_SOURCES, INTL_SOURCES, preprocess_text,
    load_json, save_json
)
from sentence_transformers import SentenceTransformer


def _encode_corpus(articles):
    """Shared helper: loads SBERT and encodes all valid articles. Returns (valid_articles, sentences, embeddings)."""
    print("Loading Sentence-BERT model (all-MiniLM-L6-v2)...")
    embedder = SentenceTransformer('all-MiniLM-L6-v2')

    valid_articles = [a for a in articles if len(f"{a.get('title', '')} {a.get('description', '')}") > 30]
    corpus_sentences = [f"{a.get('title', '')}. {a.get('description', '')}" for a in valid_articles]
    
    cache_path = os.path.join('data', 'sbert_cache.npy')
    if os.path.exists(cache_path):
        print(f"Loading cached SBERT embeddings from {cache_path}...")
        corpus_embeddings = np.load(cache_path)
        if len(corpus_embeddings) != len(corpus_sentences):
            print("Cache size mismatch, re-encoding...")
            corpus_embeddings = embedder.encode(corpus_sentences, show_progress_bar=True)
            np.save(cache_path, corpus_embeddings)
    else:
        print(f"Encoding {len(valid_articles)} articles with SBERT...")
        corpus_embeddings = embedder.encode(corpus_sentences, show_progress_bar=True)
        np.save(cache_path, corpus_embeddings)
        
    return valid_articles, corpus_sentences, corpus_embeddings


def _extract_cluster_keywords(cluster_texts, num_clusters, output_path, header):
    """Shared helper: TF-IDF keyword extraction per cluster; prints and saves to output_path."""
    docs_per_cluster = [" ".join(cluster_texts[i]) for i in range(num_clusters)]
    vectorizer = TfidfVectorizer(max_features=20)
    tfidf_matrix = vectorizer.fit_transform(docs_per_cluster)
    feature_names = vectorizer.get_feature_names_out()

    topics_text = []
    print(f"\n--- {header} ---")
    for i in range(num_clusters):
        row = tfidf_matrix.getrow(i).toarray()[0]
        top_indices = row.argsort()[-10:][::-1]
        top_words = [feature_names[j] for j in top_indices]
        label = f"Cluster {i}: " + ", ".join(top_words)
        print(label)
        topics_text.append(label)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(topics_text))


def run_kmeans(articles, num_clusters=8):
    """
    SBERT + KMeans pipeline (original).
    Soft cluster probabilities are approximated via a temperature-scaled softmax
    over Euclidean distances to centroids, stored in article['topic_vector'].
    """
    valid_articles, corpus_sentences, corpus_embeddings = _encode_corpus(articles)

    print(f"Clustering with KMeans (K={num_clusters})...")
    km = KMeans(n_clusters=num_clusters, random_state=42, n_init='auto')
    km.fit(corpus_embeddings)
    cluster_assignment = km.labels_
    distances = km.transform(corpus_embeddings)  # shape: (N, K)

    cluster_texts = {i: [] for i in range(num_clusters)}
    for idx, cluster_id in enumerate(cluster_assignment):
        clean_text = " ".join(preprocess_text(corpus_sentences[idx]))
        cluster_texts[cluster_id].append(clean_text)

        # Calculate soft assignment probabilities via a distance-based softmax
        # A temperature hyperparameter is employed to control distribution sharpness
        dist = distances[idx]
        temp = 0.05
        shifted = dist - np.min(dist)
        exp_d = np.exp(-shifted / temp)
        weights = exp_d / np.sum(exp_d)

        valid_articles[idx]['topic_vector'] = {f"topic_{t}": float(weights[t]) for t in range(num_clusters)}

    _extract_cluster_keywords(cluster_texts, num_clusters, TOPICS_OUTPUT_SBERT, "SBERT + KMeans Clusters")
    return articles


def run_gmm(articles, num_clusters=8, temperature=35.0):
    """
    SBERT + Gaussian Mixture Model pipeline.
    Uses a temperature-scaled posterior P(cluster | article) to ensure 
    topic distributions represent a spectrum rather than a binary assignment.
    """
    valid_articles, corpus_sentences, corpus_embeddings = _encode_corpus(articles)

    print(f"Fitting Gaussian Mixture Model (K={num_clusters}, covariance='spherical')...")
    print("  (Expectation-Maximization optimisation in progress, please wait.)")
    
    # Using 'spherical' covariance to prevent variance collapse in high-dimensional (384D) SBERT space.
    # This also naturally aligns the GMM clusters much more closely with KMeans centroids.
    gmm = GaussianMixture(
        n_components=num_clusters,
        covariance_type='spherical',   
        random_state=42,
        max_iter=200,
        init_params='kmeans'
    )
    gmm.fit(corpus_embeddings)
    
    # We manually calculate temperature-scaled responsibilities.
    # predict_proba() can be very "sharp" in high dimensions.
    # log_resp = log_weighted_prob - log_sum_exp(log_weighted_prob)
    
    # estimate_weighted_log_prob returns the log-likelihood of each sample 
    # for each component: log P(x | cluster_k) + log weight_k
    weighted_log_probs = gmm._estimate_weighted_log_prob(corpus_embeddings)
    
    # Apply temperature scaling to the log-probabilities to "soften" the distribution
    # T > 1.0 makes the distribution flatter (more spectrum-like)
    # T < 1.0 makes it sharper (more binary)
    soft_log_probs = weighted_log_probs / temperature
    
    # Softmax over clusters for each article
    def softmax(x):
        e_x = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e_x / e_x.sum(axis=1, keepdims=True)

    posterior_probs = softmax(soft_log_probs)
    cluster_assignment = np.argmax(posterior_probs, axis=1)

    print(f"  GMM converged: {gmm.converged_}  |  Log-likelihood: {gmm.lower_bound_:.4f}")

    cluster_texts = {i: [] for i in range(num_clusters)}
    for idx, cluster_id in enumerate(cluster_assignment):
        clean_text = " ".join(preprocess_text(corpus_sentences[idx]))
        cluster_texts[cluster_id].append(clean_text)

        # Scaled posterior: P(cluster_k | article) for each k
        probs = posterior_probs[idx]
        valid_articles[idx]['gmm_topic_vector'] = {f"topic_{t}": float(probs[t]) for t in range(num_clusters)}

    _extract_cluster_keywords(cluster_texts, num_clusters, TOPICS_OUTPUT_GMM, "SBERT + GMM Clusters")
    return articles

def main():
    parser = argparse.ArgumentParser(description="Run Topic Modeling on News Data")
    parser.add_argument("--topics", type=int, default=8, help="Number of topics/clusters (default: 8)")
    parser.add_argument(
        "--method", choices=['kmeans', 'gmm'], default='kmeans',
        help="Clustering algorithm to use: 'kmeans' (default) or 'gmm'"
    )
    parser.add_argument("--temp", type=float, default=35.0, help="Temperature for GMM softening (default: 35.0)")
    args = parser.parse_args()

    articles = load_json(DATA_PATH)
    if not articles:
        print("No articles found in data/news_data.json.")
        return

    if args.method == 'gmm':
        print(f"Running Topic Modeling Framework (SBERT + GMM) with T={args.temp}...")
        updated_articles = run_gmm(articles, args.topics, args.temp)
        save_json(DATA_PATH, updated_articles)
        print(f"\nSuccessfully updated {DATA_PATH} with GMM embeddings (field: 'gmm_topic_vector').")
    else:
        print("Running Topic Modeling Framework (SBERT + KMeans)...")
        updated_articles = run_kmeans(articles, args.topics)
        save_json(DATA_PATH, updated_articles)
        print(f"\nSuccessfully updated {DATA_PATH} with KMeans embeddings (field: 'topic_vector').")


if __name__ == "__main__":
    main()
