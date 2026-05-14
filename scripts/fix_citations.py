import re
import sys

with open('FYP_Report_utf8.txt', 'r', encoding='utf-8') as f:
    text = f.read()

refs_start = text.find('REFERENCES')
body = text[:refs_start]
refs_section = text[refs_start:]

# Fix the duplicate: [30] is the same as [22]. Replace [30] in the body with [22].
body = re.sub(r'\[30\]', '[22]', body)

# Find all unique citations in the body
# Note: we look for [number]
cited_ids_str = set(re.findall(r'\[(\d+)\]', body))
cited_ids = sorted([int(x) for x in cited_ids_str])

print("Cited IDs after dedup:", cited_ids)

# Parse the references section
# A reference starts with ^\[\d+\] and continues until the next ^\[\d+\] or end of file
ref_pattern = re.compile(r'^\[(\d+)\](.*?)(?=^\[\d+\]|\Z)', re.MULTILINE | re.DOTALL)
references = {}
for match in ref_pattern.finditer(refs_section):
    ref_id = int(match.group(1))
    ref_text = match.group(2).strip()
    references[ref_id] = ref_text

# Create a mapping from old_id to new_id to remove gaps
old_to_new = {}
new_id = 1
for old_id in cited_ids:
    old_to_new[old_id] = new_id
    new_id += 1

print("Mapping:", old_to_new)

# Replace in body. We have to be careful not to replace [15] when we mean [1].
# We can use a lambda to replace accurately
def replace_citation(match):
    num = int(match.group(1))
    if num in old_to_new:
        return f"[{old_to_new[num]}]"
    return match.group(0)

new_body = re.sub(r'\[(\d+)\]', replace_citation, body)

# Build new references section
new_refs_lines = ["REFERENCES\n"]
for old_id in cited_ids:
    if old_id in references:
        new_id = old_to_new[old_id]
        # Ensure we keep the reference text formatted nicely, maybe replace internal newlines if needed, 
        # but let's just keep it as is.
        ref_text = references[old_id]
        new_refs_lines.append(f"[{new_id}] {ref_text}\n")
    else:
        print(f"WARNING: Cited ID {old_id} not found in references section!")

new_text = new_body + "".join(new_refs_lines)

with open('FYP_Report_utf8.txt', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Citations fixed and file updated successfully.")
