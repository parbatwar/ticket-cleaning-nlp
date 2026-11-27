"""
Task 1: Clean noisy helpdesk tickets and run basic NLP preprocessing.

Removes duplicates and unusable rows, normalises the query text, tokenises it,
and reports category counts and the most frequent keywords.

Uses the standard library only. Run:
    python task1_nlp_cleaner.py
"""

import json
import re
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "data" / "support_tickets.json"
OUTPUT_PATH = BASE_DIR / "data" / "cleaned_tickets.json"

STOP_WORDS = {
    "the", "is", "on", "and", "do", "i", "my", "to",
    "from", "or", "can", "how", "what", "after",
}

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
NON_ALPHANUMERIC_PATTERN = re.compile(r"[^a-z0-9\s]")


def load_tickets(path=INPUT_PATH):
    """Read the raw ticket list from a JSON file."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def strip_html(text):
    """Remove HTML tags such as <br>, replacing each with a space."""
    return HTML_TAG_PATTERN.sub(" ", text)


def is_valid_query(query):
    """Return True if the query exists and contains visible characters."""
    return bool(query and query.strip())


def clean_tickets(tickets):
    """
    Drop duplicate and unusable tickets, and normalise the query text.

    Keeps the first occurrence of each ticket_id.
    """
    seen_ids = set()
    cleaned = []

    for ticket in tickets:
        ticket_id = ticket.get("ticket_id")
        if ticket_id in seen_ids:
            continue

        query = ticket.get("query")
        if not is_valid_query(query):
            # Not added to seen_ids: a later valid row with this id is still wanted.
            continue

        text = strip_html(query)
        text = " ".join(text.split())

        seen_ids.add(ticket_id)

        cleaned_ticket = dict(ticket)
        cleaned_ticket["query"] = text
        cleaned.append(cleaned_ticket)

    return cleaned


def simple_stem(word):
    """
    Strip common suffixes so word variants count as one keyword.

    The length guard prevents over-stemming short words ("days" -> "dai").
    """
    for suffix in ("ing", "ies", "es", "ed", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            stem = word[: -len(suffix)]
            return stem + "y" if suffix == "ies" else stem
    return word


def preprocess_text(text, apply_stemming=True):
    """Lowercase, strip punctuation, tokenise and remove stop words."""
    text = text.lower()
    # Replaced with a space, not removed, so "travel&meal" splits into two tokens.
    text = NON_ALPHANUMERIC_PATTERN.sub(" ", text)

    tokens = [token for token in text.split() if token not in STOP_WORDS]

    if apply_stemming:
        tokens = [simple_stem(token) for token in tokens]

    return tokens


def analyze_tickets(cleaned_tickets, top_n=5, output_path=OUTPUT_PATH):
    """Count tickets per category and keyword frequencies, and save the records."""
    category_counts = Counter()
    keyword_counts = Counter()
    records = []

    for ticket in cleaned_tickets:
        category_counts[ticket.get("category", "Uncategorised")] += 1

        tokens = preprocess_text(ticket["query"])
        keyword_counts.update(tokens)

        record = dict(ticket)
        record["tokens"] = tokens
        records.append(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)

    return {
        "total_valid_tickets": len(cleaned_tickets),
        "counts_per_category": dict(category_counts),
        "top_keywords": keyword_counts.most_common(top_n),
        "output_file": str(output_path),
    }


def main():
    raw_tickets = load_tickets()
    cleaned_tickets = clean_tickets(raw_tickets)
    summary = analyze_tickets(cleaned_tickets)

    print(f"Loaded {len(raw_tickets)} raw tickets")
    print(f"Kept {summary['total_valid_tickets']} after cleaning\n")

    print("Tickets per category:")
    for category, count in sorted(summary["counts_per_category"].items()):
        print(f"  {category:<10} {count}")

    print(f"\nTop {len(summary['top_keywords'])} keywords:")
    for rank, (word, count) in enumerate(summary["top_keywords"], start=1):
        print(f"  {rank}. {word:<15} {count}")

    print(f"\nCleaned records written to {summary['output_file']}")


if __name__ == "__main__":
    main()
