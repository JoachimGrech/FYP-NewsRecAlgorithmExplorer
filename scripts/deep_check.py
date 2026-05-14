"""
deep_check.py - Investigate the specific issues found in backend_smoke_test.
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

with open('../data/news_data.json', 'r', encoding='utf-8') as f:
    articles = json.load(f)
with open('../data/user_profiles.json', 'r', encoding='utf-8') as f:
    profiles = json.load(f)

import recommend, recommend_gmm

# ── 1. Check what recommend_articles actually returns ─────────────────────────
print("=== 1. What does recommend_articles return? ===")
user = profiles[0]
result = recommend.recommend_articles(user, articles, num_recommendations=5, diversity_score=0.0)
print(f"Type: {type(result).__name__}, Length: {len(result)}")
if result:
    print(f"result[0] type: {type(result[0]).__name__}")
    print(f"result[0] content: {str(result[0])[:200]}")

# ── 2. Check what recommend_articles_gmm returns ──────────────────────────────
print("\n=== 2. What does recommend_articles_gmm return? ===")
result_gmm = recommend_gmm.recommend_articles_gmm(user, articles, num_recommendations=5)
print(f"Type: {type(result_gmm).__name__}, Length: {len(result_gmm)}")
if result_gmm:
    print(f"result_gmm[0] type: {type(result_gmm[0]).__name__}")
    print(f"result_gmm[0] content: {str(result_gmm[0])[:200]}")

# ── 3. Why only 2 items returned instead of 5? ───────────────────────────────
print("\n=== 3. Why only 2 results? (expected 5) ===")
print("User reading_history length:", len(user.get('reading_history', [])))
print("Sample history item:", str(user.get('reading_history', [])[0])[:120])

# Check how recommend.py matches history items to articles
import inspect
src = inspect.getsource(recommend.recommend_articles)
# Find the key matching logic
lines = [l.strip() for l in src.split('\n') if 'link' in l.lower() or 'match' in l.lower() or 'history' in l.lower()]
print("Key logic lines from recommend_articles:")
for l in lines[:10]:
    print(" ", l)

# ── 4. Vector shape issue: 1135 articles with wrong topic_vector size ─────────
print("\n=== 4. topic_vector invalid articles (expected 8 keys) ===")
bad = [a for a in articles if not (isinstance(a.get('topic_vector'), dict) and len(a.get('topic_vector', {})) == 8)]
print(f"Count: {len(bad)}")
if bad:
    b = bad[0]
    tv = b.get('topic_vector')
    print(f"Bad article title: {b.get('title','?')[:60]}")
    print(f"topic_vector type: {type(tv).__name__}, value: {str(tv)[:100]}")

# ── 5. gmm_topic_vector invalid articles (21 articles) ───────────────────────
print("\n=== 5. gmm_topic_vector invalid articles (expected 8 keys) ===")
bad_gmm = [a for a in articles if not (isinstance(a.get('gmm_topic_vector'), dict) and len(a.get('gmm_topic_vector', {})) == 8)]
print(f"Count: {len(bad_gmm)}")
if bad_gmm:
    b2 = bad_gmm[0]
    gv = b2.get('gmm_topic_vector')
    print(f"Bad article title: {b2.get('title','?')[:60]}")
    print(f"gmm_topic_vector type: {type(gv).__name__}, value: {str(gv)[:100]}")
