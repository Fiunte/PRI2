import json
from collections import defaultdict
import os

data_path = os.path.join("..", "data.json")
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

if not data:
    print("No data found.")
    exit()

# Collect all fields
fields = data[0].keys()

unique_fields = []

for field in fields:
    seen = set()
    duplicate_found = False
    missing_found = False
    
    for doc in data:
        if field not in doc or doc[field] is None:
            missing_found = True
            break
        
        value = doc.get(field)
        
        # For multi-valued fields (lists), convert to tuple to store in set
        if isinstance(value, list):
            value = tuple(value)
        
        if value in seen:
            duplicate_found = True
            break
        seen.add(value)
    
    if not duplicate_found:
        unique_fields.append((field, not missing_found))  # True if field exists for all docs

print("Fields that are unique across all documents:")
for f, exists_in_all in unique_fields:
    status = "exists in all docs" if exists_in_all else "missing in some docs"
    print(f"{f}: {status}")
