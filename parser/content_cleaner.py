import re
import json
import os

class ContentCleaner:
    def normalize_whitespace(self, text):
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    def remove_control_chars(self, text):
        return re.sub(r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]", "", text)

    def clean(self, item):
        title = item.get("title") or ""
        content = item.get("content") or ""

        title = self.remove_control_chars(title)
        content = self.remove_control_chars(content)

        title = self.normalize_whitespace(title)
        content = self.normalize_whitespace(content)

        item["title"] = title
        item["content"] = content

        return item

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(__file__))
    raw_path = os.path.join(base_dir, "data", "isna_sample.json")
    cleaned_dir = os.path.join(base_dir, "data", "cleaned")
    os.makedirs(cleaned_dir, exist_ok=True)
    cleaned_path = os.path.join(cleaned_dir, "isna_cleaned.json")

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaner = ContentCleaner()
    cleaned = [cleaner.clean(x) for x in data]

    with open(cleaned_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
