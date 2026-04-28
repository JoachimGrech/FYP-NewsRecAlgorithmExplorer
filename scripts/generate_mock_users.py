import json
import random
import os

data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'news_data.json')
output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'mock_users.json')

with open(data_path, 'r', encoding='utf-8') as f:
    articles = json.load(f)

# Group articles by dominant topic
topic_buckets = {f"topic_{i}": [] for i in range(8)}
for a in articles:
    if 'topic_vector' in a and a['topic_vector']:
        dom_topic = max(a['topic_vector'], key=a['topic_vector'].get)
        topic_buckets[dom_topic].append(a['link'])

all_topics = list(topic_buckets.keys())
mock_users = []
NUM_USERS = 1000

# Define richer user archetype profiles for diversity
# Each archetype: (description, primary_bias_pct, secondary_bias_pct, noise_pct, num_primary_topics, history_range)
ARCHETYPES = [
    # --- Single-topic "Filter Bubble" readers ---
    ("hardcore_fan",    0.90, 0.08, 0.02, 1, (15, 40)),   # Obsessive single-topic reader
    ("casual_follower", 0.75, 0.20, 0.05, 1, (5, 15)),    # Relaxed single-topic reader

    # --- Dual-topic "Niche" readers ---
    ("dual_niche",      0.50, 0.40, 0.10, 2, (10, 30)),   # Two strong interests
    ("primary_leaner",  0.65, 0.25, 0.10, 2, (8, 25)),    # Two interests, one dominant

    # --- Broad "Omnivore" readers ---
    ("eclectic",        0.30, 0.30, 0.40, 3, (20, 50)),   # 3 topics + lots of random
    ("news_junkie",     0.25, 0.25, 0.50, 4, (30, 60)),   # Heavy reader across many topics

    # --- Light / Casual browsing ---
    ("light_browser",   0.60, 0.30, 0.10, 1, (3, 8)),     # Reads very little
    ("occasional",      0.55, 0.25, 0.20, 2, (4, 10)),    # Sporadic reader
]

for i in range(NUM_USERS):
    archetype = random.choice(ARCHETYPES)
    arch_name, primary_pct, secondary_pct, noise_pct, num_primary, hist_range = archetype

    # Pick this user's "primary" topics (no repeats)
    primary_topics = random.sample(all_topics, min(num_primary, len(all_topics)))
    other_topics = [t for t in all_topics if t not in primary_topics]

    num_read = random.randint(*hist_range)
    primary_count  = int(num_read * primary_pct)
    secondary_count = int(num_read * secondary_pct)
    noise_count    = num_read - primary_count - secondary_count

    history_links = set()

    # Primary reads – split evenly across primary topics
    per_primary = max(1, primary_count // len(primary_topics))
    for pt in primary_topics:
        pool = topic_buckets[pt]
        if pool:
            take = min(per_primary, len(pool))
            history_links.update(random.sample(pool, take))

    # Secondary reads – from one or two other topics
    secondary_topics = random.sample(other_topics, min(2, len(other_topics))) if other_topics else []
    for _ in range(secondary_count):
        if secondary_topics:
            st = random.choice(secondary_topics)
            if topic_buckets[st]:
                history_links.add(random.choice(topic_buckets[st]))

    # Noise – fully random across ALL topics
    for _ in range(noise_count):
        rt = random.choice(all_topics)
        if topic_buckets[rt]:
            history_links.add(random.choice(topic_buckets[rt]))

    mock_users.append({
        "id": f"mock_user_{i}",
        "archetype": arch_name,
        "bias": primary_topics[0],          # Primary topic label (for debugging)
        "reading_history": list(history_links)
    })

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(mock_users, f, indent=2)

# Print breakdown by archetype
arch_counts = {}
for u in mock_users:
    arch_counts[u['archetype']] = arch_counts.get(u['archetype'], 0) + 1

print(f"\nGenerated {NUM_USERS} mock users across {len(ARCHETYPES)} behavioural archetypes:\n")
for arch, count in sorted(arch_counts.items(), key=lambda x: -x[1]):
    print(f"  {arch:<20} {count} users")
print(f"\nSaved to: {output_path}")
