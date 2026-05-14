"""
backend_smoke_test.py
Tests the actual recommend.py and recommend_gmm.py with the real data schema.
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

with open('../data/news_data.json', 'r', encoding='utf-8') as f:
    articles = json.load(f)

with open('../data/user_profiles.json', 'r', encoding='utf-8') as f:
    profiles = json.load(f)

print(f"Loaded {len(articles)} articles, {len(profiles)} user profiles")
print(f"Article schema: {list(articles[0].keys())}")
print(f"Profile schema: {list(profiles[0].keys())}")

# ── K-Means recommender ───────────────────────────────────────────────────────
print("\n--- K-Means Smoke Test ---")
import recommend
user = profiles[0]
print(f"Testing with user: {user.get('name','?')} | history items: {len(user.get('reading_history',[]))}")
try:
    recs = recommend.recommend_articles(user, articles, num_recommendations=5, diversity_score=0.0)
    print(f"[PASS] recommend_articles returned {len(recs)} items")
    for i, r in enumerate(recs):
        score = r.get('score', r.get('similarity', '?'))
        title = r.get('title', '?')[:55]
        print(f"  {i+1}. [{score:.4f}] {title}")
except Exception as e:
    import traceback
    print(f"[FAIL] {traceback.format_exc()}")

# ── GMM recommender ───────────────────────────────────────────────────────────
print("\n--- GMM Smoke Test ---")
import recommend_gmm
try:
    recs_gmm = recommend_gmm.recommend_articles_gmm(user, articles, num_recommendations=5)
    print(f"[PASS] recommend_articles_gmm returned {len(recs_gmm)} items")
    for i, r in enumerate(recs_gmm):
        score = r.get('score', r.get('similarity', '?'))
        title = r.get('title', '?')[:55]
        print(f"  {i+1}. [{score:.4f}] {title}")
except Exception as e:
    import traceback
    print(f"[FAIL] {traceback.format_exc()}")

# ── Diversity injection test ──────────────────────────────────────────────────
print("\n--- Diversity Injection Test (diversity=0.3) ---")
try:
    recs_d = recommend.recommend_articles(user, articles, num_recommendations=5, diversity_score=0.3)
    print(f"[PASS] returned {len(recs_d)} items")
    discoveries = [r for r in recs_d if r.get('type') == 'discovery' or r.get('is_discovery')]
    print(f"  Regular: {len(recs_d)-len(discoveries)}, Discoveries: {len(discoveries)}")
except Exception as e:
    print(f"[FAIL] {e}")

# ── Vector shape validation ───────────────────────────────────────────────────
print("\n--- Vector Shape Validation ---")
ok_tv, ok_gmm = 0, 0
bad_tv, bad_gmm = 0, 0
for a in articles:
    tv = a.get('topic_vector', {})
    gv = a.get('gmm_topic_vector', {})
    if isinstance(tv, dict) and len(tv) == 8: ok_tv += 1
    else: bad_tv += 1
    if isinstance(gv, dict) and len(gv) == 8: ok_gmm += 1
    else: bad_gmm += 1
print(f"topic_vector:     {ok_tv} valid, {bad_tv} invalid (expected 8 keys)")
print(f"gmm_topic_vector: {ok_gmm} valid, {bad_gmm} invalid (expected 8 keys)")

# ── Evaluate comparison import & quick run ────────────────────────────────────
print("\n--- Evaluate Comparison Functions ---")
import evaluate_comparison as ec
import inspect
fns = [n for n,o in inspect.getmembers(ec, inspect.isfunction) if not n.startswith('_')]
print(f"Available functions: {fns}")

# ── SBERT cache alignment ─────────────────────────────────────────────────────
print("\n--- SBERT Cache Alignment ---")
import numpy as np
cache = np.load('../data/sbert_cache.npy')
print(f"cache shape: {cache.shape}")
print(f"articles: {len(articles)}")
diff = abs(cache.shape[0] - len(articles))
if diff == 0:
    print("[PASS] Cache row count matches article count exactly")
elif diff <= 30:
    print(f"[WARN] {diff} row discrepancy — likely from articles added after last SBERT run")
else:
    print(f"[FAIL] Large discrepancy: {diff} rows — SBERT cache needs regeneration")

print("\n=== BACKEND CHECK COMPLETE ===")
