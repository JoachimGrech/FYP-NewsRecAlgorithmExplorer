"""
system_check.py
Comprehensive end-to-end integrity check for the FYP news recommender system.
Checks: data files, clustering vectors, recommenders, evaluation pipeline, frontend assets.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import json, sys, os, traceback
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
DATA = os.path.join(ROOT, "data")
FRONTEND = os.path.join(ROOT, "frontend")
EXPERIMENTS = os.path.join(DATA, "experiments")

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

issues = []

def check(label, condition, detail="", fatal=False):
    if condition:
        print(f"  {PASS} {label}")
        if detail:
            print(f"         {detail}")
    else:
        tag = FAIL if fatal else WARN
        print(f"  {tag} {label}")
        if detail:
            print(f"         {detail}")
        issues.append(f"{tag} {label}: {detail}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  1. DATA FILES")
print("══════════════════════════════════════════════")

# news_data.json
news_path = os.path.join(DATA, "news_data.json")
check("news_data.json exists", os.path.exists(news_path), fatal=True)
try:
    with open(news_path, "r", encoding="utf-8") as f:
        articles = json.load(f)
    check("news_data.json parses", True, f"{len(articles)} articles loaded")
    sample = articles[0]
    keys = list(sample.keys())
    check("Articles have 'title'", "title" in keys)
    check("Articles have 'content' or 'text'", "content" in keys or "text" in keys, str(keys))
    check("Articles have 'kmeans_vector'", "kmeans_vector" in keys)
    check("Articles have 'gmm_vector'", "gmm_vector" in keys)
    if "kmeans_vector" in keys:
        kv = sample["kmeans_vector"]
        check("kmeans_vector is length 8", len(kv) == 8, f"length={len(kv)}")
    if "gmm_vector" in keys:
        gv = sample["gmm_vector"]
        check("gmm_vector is length 8", len(gv) == 8, f"length={len(gv)}")
        check("gmm_vector sums to ~1.0", abs(sum(gv) - 1.0) < 0.01, f"sum={sum(gv):.4f}")
except Exception as e:
    print(f"  {FAIL} news_data.json failed: {e}")
    issues.append(str(e))

# sbert_cache.npy
cache_path = os.path.join(DATA, "sbert_cache.npy")
check("sbert_cache.npy exists", os.path.exists(cache_path))
try:
    cache = np.load(cache_path)
    check("sbert_cache shape valid", len(cache.shape) == 2, f"shape={cache.shape}")
    check("sbert_cache rows match articles", cache.shape[0] == len(articles),
          f"cache={cache.shape[0]}, articles={len(articles)}")
    check("sbert_cache dim is 384", cache.shape[1] == 384, f"dim={cache.shape[1]}")
except Exception as e:
    print(f"  {WARN} sbert_cache.npy check failed: {e}")

# user_profiles.json
up_path = os.path.join(DATA, "user_profiles.json")
check("user_profiles.json exists", os.path.exists(up_path))
try:
    with open(up_path, "r", encoding="utf-8") as f:
        profiles = json.load(f)
    check("user_profiles.json parses", True, f"{len(profiles)} profiles")
    sample_user = list(profiles.values())[0]
    check("Profiles have 'vector'", "vector" in sample_user or "kmeans_vector" in sample_user,
          str(list(sample_user.keys())))
    check("Profiles have 'history'", "history" in sample_user)
except Exception as e:
    print(f"  {WARN} user_profiles.json check failed: {e}")

# mock_users.json
mu_path = os.path.join(DATA, "mock_users.json")
check("mock_users.json exists", os.path.exists(mu_path))
try:
    with open(mu_path, "r", encoding="utf-8") as f:
        mock = json.load(f)
    check("mock_users.json parses", True, f"{len(mock)} mock users")
    s = mock[0]
    check("Mock users have 'history'", "history" in s)
    h0 = s["history"][0] if s.get("history") else None
    check("History items are dicts (not plain IDs)",
          isinstance(h0, dict), f"type={type(h0).__name__}")
except Exception as e:
    print(f"  {WARN} mock_users.json check failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  2. EXPERIMENT FIGURES")
print("══════════════════════════════════════════════")

required_figs = [
    "top_n_vs_relevance.png",
    "top_n_vs_coverage.png",
    "diversity_vs_relevance.png",
    "diversity_vs_ils.png",
    "k_vs_relevance.png",
    "archetype_relevance.png",
]
for fig in required_figs:
    p = os.path.join(EXPERIMENTS, fig)
    size = os.path.getsize(p) if os.path.exists(p) else 0
    check(f"Figure exists: {fig}", os.path.exists(p), f"size={size//1024}KB")

extra_figs = [f for f in os.listdir(EXPERIMENTS) if f not in required_figs]
check("No unexpected figures in experiments/", len(extra_figs) == 0,
      f"Extra files: {extra_figs}" if extra_figs else "")

# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  3. PYTHON SCRIPTS — IMPORT CHECK")
print("══════════════════════════════════════════════")

for script in ["recommend", "recommend_gmm", "evaluate_comparison", "run_topic_modeling"]:
    try:
        mod = __import__(script)
        check(f"{script}.py imports cleanly", True)
    except Exception as e:
        check(f"{script}.py imports cleanly", False, str(e)[:120])

# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  4. RECOMMENDER SMOKE TEST (K-Means)")
print("══════════════════════════════════════════════")
try:
    import recommend
    test_articles = articles[:200]
    # Build a fake user vector (uniform)
    user_vec = [1/8] * 8
    recs = recommend.get_recommendations(user_vec, test_articles, top_n=5, diversity=0.0)
    check("K-Means recommender returns results", len(recs) > 0, f"returned {len(recs)} recs")
    check("K-Means recs have 'title'", "title" in recs[0], str(list(recs[0].keys()))[:80])
    check("K-Means recs have 'score'", "score" in recs[0], str(list(recs[0].keys()))[:80])
    scores = [r["score"] for r in recs]
    check("K-Means scores are 0-1", all(0 <= s <= 1 for s in scores), str(scores))
    check("K-Means scores are sorted descending",
          scores == sorted(scores, reverse=True), str(scores))
except Exception as e:
    check("K-Means recommender smoke test", False, traceback.format_exc()[:200])

# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  5. RECOMMENDER SMOKE TEST (GMM)")
print("══════════════════════════════════════════════")
try:
    import recommend_gmm
    test_history = [articles[i]["id"] for i in range(5) if "id" in articles[i]]
    if not test_history:
        # Try using index-based
        test_history = list(range(5))
    recs_gmm = recommend_gmm.get_gmm_recommendations(test_history, articles[:200], top_n=5)
    check("GMM recommender returns results", len(recs_gmm) > 0, f"returned {len(recs_gmm)} recs")
    check("GMM recs have 'title'", "title" in recs_gmm[0], str(list(recs_gmm[0].keys()))[:80])
    check("GMM recs have 'score'", "score" in recs_gmm[0], str(list(recs_gmm[0].keys()))[:80])
    scores_gmm = [r["score"] for r in recs_gmm]
    check("GMM scores are 0-1", all(0 <= s <= 1 for s in scores_gmm), str(scores_gmm))
except Exception as e:
    check("GMM recommender smoke test", False, traceback.format_exc()[:300])

# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  6. FRONTEND ASSETS")
print("══════════════════════════════════════════════")
for asset in ["index.html", "app.js", "styles.css"]:
    p = os.path.join(FRONTEND, asset)
    size = os.path.getsize(p) if os.path.exists(p) else 0
    check(f"{asset} exists", os.path.exists(p), f"size={size//1024}KB")

# Check index.html references app.js and styles.css
try:
    with open(os.path.join(FRONTEND, "index.html"), "r", encoding="utf-8") as f:
        html = f.read()
    check("index.html references app.js", "app.js" in html)
    check("index.html references styles.css", "styles.css" in html)
    check("index.html references Chart.js", "chart" in html.lower())
    check("index.html references news_data.json", "news_data.json" in html)
    check("index.html references user_profiles.json", "user_profiles.json" in html)
except Exception as e:
    check("index.html read", False, str(e))

# Check app.js for key functions
try:
    with open(os.path.join(FRONTEND, "app.js"), "r", encoding="utf-8") as f:
        js = f.read()
    check("app.js has getRecommendations function", "getRecommendations" in js or "recommend" in js.lower())
    check("app.js has GMM toggle", "gmm" in js.lower())
    check("app.js has drawProjector/community map", "drawProjector" in js or "projector" in js.lower())
    check("app.js has radar chart logic", "radar" in js.lower() or "Radar" in js)
    check("app.js has diversity slider", "diversity" in js.lower())
    check("app.js has cosine similarity", "cosine" in js.lower() or "cosineSim" in js)
except Exception as e:
    check("app.js read", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════")
print("  SUMMARY")
print("══════════════════════════════════════════════")
if not issues:
    print("  All checks passed. System is healthy.")
else:
    print(f"  {len(issues)} issue(s) found:")
    for issue in issues:
        print(f"    {issue}")
