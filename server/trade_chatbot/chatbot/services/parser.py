import re

def parse_query(message):
    message = message.lower()

    data_type = "Import" if "import" in message else "Export"

    # Convert 2025 → 2024
    year_match = re.search(r"\b(20\d{2})\b", message)
    if year_match:
        year = str(int(year_match.group(1)) - 1)
    else:
        year = "2024"

    skip_words = ["i", "need", "data", "for", "in", "the", "export", "import"]

    words = message.replace(",", "").split()

    country_words = [
        w for w in words
        if w not in skip_words and not w.isdigit()
    ]

    country = " ".join(country_words).title()

    return data_type, country, year