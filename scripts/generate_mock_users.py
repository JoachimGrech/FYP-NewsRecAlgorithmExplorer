import json
import random
import os

def generate_users(articles, num_clusters=8, num_users=500):
    # Group articles by dominant topic
    topic_buckets = {f"topic_{i}": [] for i in range(num_clusters)}
    for a in articles:
        # Check for both topic_vector and gmm_topic_vector
        vec = a.get('topic_vector') or a.get('gmm_topic_vector')
        if vec:
            dom_topic = max(vec, key=vec.get)
            if dom_topic in topic_buckets:
                # Store the whole article (or at least the necessary parts)
                topic_buckets[dom_topic].append({
                    'link': a['link'],
                    'title': a.get('title', ''),
                    'topic_vector': a.get('topic_vector'),
                    'gmm_topic_vector': a.get('gmm_topic_vector')
                })

    all_topics = list(topic_buckets.keys())
    mock_users = []

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

    for i in range(num_users):
        archetype = random.choice(ARCHETYPES)
        arch_name, primary_pct, secondary_pct, noise_pct, num_primary, hist_range = archetype

        # Pick this user's "primary" topics (no repeats)
        primary_topics = random.sample(all_topics, min(num_primary, len(all_topics)))
        other_topics = [t for t in all_topics if t not in primary_topics]

        num_read = random.randint(*hist_range)
        primary_count  = int(num_read * primary_pct)
        secondary_count = int(num_read * secondary_pct)
        noise_count    = num_read - primary_count - secondary_count

        history_list = []

        # Primary reads – split evenly across primary topics
        per_primary = max(1, primary_count // len(primary_topics))
        for pt in primary_topics:
            pool = topic_buckets.get(pt, [])
            if pool:
                take = min(per_primary, len(pool))
                history_list.extend(random.sample(pool, take))

        # Secondary reads – from one or two other topics
        secondary_topics = random.sample(other_topics, min(2, len(other_topics))) if other_topics else []
        for _ in range(secondary_count):
            if secondary_topics:
                st = random.choice(secondary_topics)
                if topic_buckets.get(st):
                    history_list.append(random.choice(topic_buckets[st]))

        # Noise – fully random across ALL topics
        for _ in range(noise_count):
            rt = random.choice(all_topics)
            if topic_buckets.get(rt):
                history_list.append(random.choice(topic_buckets[rt]))

        mock_users.append({
            "id": f"mock_user_{i}",
            "name": f"Mock User {i} ({arch_name})",
            "description": f"A simulated {arch_name} reader leaning towards {primary_topics[0]}.",
            "archetype": arch_name,
            "bias": primary_topics[0],
            "reading_history": history_list
        })

    return mock_users

def main():
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'news_data.json')
    output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'mock_users.json')

    with open(data_path, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    mock_users = generate_users(articles, num_clusters=8, num_users=1000)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mock_users, f, indent=2)

    arch_counts = {}
    for u in mock_users:
        arch_counts[u['archetype']] = arch_counts.get(u['archetype'], 0) + 1

    print(f"\nGenerated 1000 mock users:\n")
    for arch, count in sorted(arch_counts.items(), key=lambda x: -x[1]):
        print(f"  {arch:<20} {count} users")
    print(f"\nSaved to: {output_path}")

if __name__ == "__main__":
    main()
