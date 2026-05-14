import json
import os
import sys
from utils import (
    DATA_PATH, TOPICS_OUTPUT_SBERT, VALIDATION_OUTPUT,
    load_json, preprocess_text
)

def check_stats(articles):
    print("\n--- Dataset Statistics ---")
    stats = {}
    for a in articles:
        s = a['source']
        if s not in stats:
            stats[s] = {'total': 0, 'empty_desc': 0, 'empty_full_text': 0}
        stats[s]['total'] += 1
        if not a.get('description'):
            stats[s]['empty_desc'] += 1
        if not a.get('full_text'):
            stats[s]['empty_full_text'] += 1

    print(f"{'Source':<20} | {'Total':<6} | {'No Desc':<8} | {'No Text':<8}")
    print("-" * 50)
    for s, data in stats.items():
        print(f"{s[:19]:<20} | {data['total']:<6} | {data['empty_desc']:<8} | {data['empty_full_text']:<8}")


def validate_sbert_clusters(articles):
    print(f"\n--- Validating SBERT Clusters -> {VALIDATION_OUTPUT} ---")
    
    topics_map = {}
    if os.path.exists(TOPICS_OUTPUT_SBERT):
        with open(TOPICS_OUTPUT_SBERT, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('Cluster'):
                    parts = line.split(': ', 1)
                    if len(parts) == 2:
                        t_id = parts[0].replace('Cluster ', '').strip()
                        topics_map[f"topic_{t_id}"] = parts[1].strip()

    analyzed = [a for a in articles if a.get('topic_vector')]
    if not analyzed:
        print("No topic vectors found.")
        return

    groups = {}
    for a in analyzed:
        dominant = max(a['topic_vector'].items(), key=lambda x: x[1])
        t_name, prob = dominant
        if t_name not in groups: groups[t_name] = []
        groups[t_name].append((a, prob))

    output = []
    output.append(f"{'Source':<15} | {'Conf':<4} | {'Title'}")
    output.append("-" * 80)

    for t_name, arts in sorted(groups.items()):
        arts.sort(key=lambda x: x[1], reverse=True)
        keywords = topics_map.get(t_name, "N/A")
        output.append(f"\n====== {t_name.replace('topic_', 'Cluster ')} ======")
        output.append(f"Keywords: {keywords}\n")
        
        for art, conf in arts[:5]:
            output.append(f"{art['source'][:14]:<15} | {conf:.2f} | {art['title'][:65]}...")
        output.append("-" * 80)

    with open(VALIDATION_OUTPUT, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
    print("Validation samples generated.")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze News Dataset and Topics")
    parser.add_argument("--stats", action="store_true", help="Show dataset statistics")
    parser.add_argument("--validate-sbert", action="store_true", help="Generate validation sample for SBERT clusters")
    parser.add_argument("--all", action="store_true", help="Run all analyses")
    args = parser.parse_args()

    articles = load_json(DATA_PATH)
    if not articles:
        print("Data not found.")
        return

    if args.stats or args.all:
        check_stats(articles)
    if args.validate_sbert or args.all:
        validate_sbert_clusters(articles)

    if not any([args.stats, args.validate_sbert, args.all]):
        parser.print_help()

if __name__ == "__main__":
    main()
