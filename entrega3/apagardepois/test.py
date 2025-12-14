import json
import os

def clean_text(text):
    if text is None:
        return ""
    if isinstance(text, list):
        return " ".join(text)
    return str(text)

def word_count(text):
    return len(clean_text(text).split())

# Load your data from parent folder
data_path = os.path.join("..", "data.json")
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

total_main_words = 0
total_warning_words = 0
count_main = 0
count_warning = 0

for doc in data:
    # Main text: either 'indications_and_usage' or 'purpose'
    main_text = doc.get("indications_and_usage") or doc.get("purpose")
    main_text_clean = clean_text(main_text)
    if main_text_clean.strip():
        total_main_words += word_count(main_text_clean)
        count_main += 1

    # Warnings
    warnings_text = clean_text(doc.get("warnings"))
    if warnings_text.strip():
        total_warning_words += word_count(warnings_text)
        count_warning += 1

avg_main_length = total_main_words / count_main if count_main else 0
avg_warning_length = total_warning_words / count_warning if count_warning else 0

print(f"Average words in main text (indications/purpose): {avg_main_length:.2f}")
print(f"Average words in warnings: {avg_warning_length:.2f}")
