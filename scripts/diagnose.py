"""
diagnose.py - Deep diagnostic of data schemas and function signatures.
"""
import sys, os, json, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inspect

print("=== 1. news_data.json article schema ===")
with open('../data/news_data.json', 'r', encoding='utf-8') as f:
    articles = json.load(f)
s = articles[0]
print("Keys:", list(s.keys()))
tv = s.get('topic_vector')
print("topic_vector type:", type(tv).__name__)
if isinstance(tv, dict):
    print("  topic_vector keys:", list(tv.keys())[:5])
elif isinstance(tv, list):
    print("  topic_vector len:", len(tv), "first3:", tv[:3])
gmm = s.get('gmm_topic_vector')
print("gmm_topic_vector type:", type(gmm).__name__)
if isinstance(gmm, dict):
    print("  gmm_topic_vector keys:", list(gmm.keys())[:5])
elif isinstance(gmm, list):
    print("  gmm_topic_vector len:", len(gmm), "first3:", gmm[:3])

print()
print("=== 2. user_profiles.json structure ===")
with open('../data/user_profiles.json', 'r', encoding='utf-8') as f:
    profiles = json.load(f)
print("Type:", type(profiles).__name__)
if isinstance(profiles, list):
    print("Length:", len(profiles))
    print("First item keys:", list(profiles[0].keys()))
elif isinstance(profiles, dict):
    k = list(profiles.keys())[0]
    print("Keys (dict):", list(profiles.keys()))
    print("First value keys:", list(profiles[k].keys()))

print()
print("=== 3. mock_users.json structure ===")
with open('../data/mock_users.json', 'r', encoding='utf-8') as f:
    mock = json.load(f)
s = mock[0]
print("Keys:", list(s.keys()))
hist = s.get('history', s.get('reading_history', s.get('read_articles', None)))
print("History field:", [k for k in s.keys() if 'hist' in k.lower() or 'read' in k.lower() or 'article' in k.lower()])
if hist:
    print("History[0] type:", type(hist[0]).__name__)
    print("History[0] value:", str(hist[0])[:120])
else:
    print("No history field found in keys:", list(s.keys()))

print()
print("=== 4. recommend.py & recommend_gmm.py public functions ===")
import recommend, recommend_gmm
for mod in [recommend, recommend_gmm]:
    print(f"\n{mod.__name__}:")
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        if not name.startswith('_'):
            print(f"  {name}{inspect.signature(obj)}")

print()
print("=== 5. frontend data loading (app.js) ===")
with open('../frontend/app.js', 'r', encoding='utf-8') as f:
    js = f.read()
fetches = re.findall(r"fetch\('([^']+)'\)", js) + re.findall(r'fetch\("([^"]+)"\)', js)
print("fetch() URLs in app.js:", fetches)
