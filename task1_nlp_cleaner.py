"""
Task 1: Cleaning and basic NLP preprocessing of helpdesk tickets.

Raw support tickets arrive noisy: duplicates, empty bodies, stray whitespace
and HTML left over from web forms. Before anything can be embedded or indexed
for search, that noise has to go, otherwise it ends up inside the vectors.

This script is deliberately dependency-free (standard library only) so it runs
anywhere without installation. Stemming is done with simple suffix rules rather
than NLTK for the same reason.

Run:
    python task1_nlp_cleaner.py
"""

import json
import re
from collections import Counter
from pathlib import Path

# Paths are resolved relative to this file, not the shell's working directory,
# so the script behaves the same no matter where it is run from.
BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "data" / "support_tickets.json"
OUTPUT_PATH = BASE_DIR / "data" / "cleaned_tickets.json"

# Stop words given in the brief. A set, not a list, because membership testing
# is O(1) on a set and O(n) on a list — it matters once the corpus grows.
STOP_WORDS = {
    "the", "is", "on", "and", "do", "i", "my", "to",
    "from", "or", "can", "how", "what", "after",
}

# Matches an HTML tag: '<', then anything that is not '>', then '>'.
# Compiled once at import rather than rebuilt on every call.
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

# Matches any character that is not a letter, digit or whitespace.
NON_ALPHANUMERIC_PATTERN = re.compile(r"[^a-z0-9\s]")


def load_tickets(path=INPUT_PATH):
    """Read the raw ticket list from a JSON file."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def strip_html(text):
    """Remove HTML tags such as <br> or <b>...</b>, keeping the inner text."""
    return HTML_TAG_PATTERN.sub(" ", text)


def is_valid_query(query):
    """
    A query is usable only if it exists and holds visible characters.

    Three separate failure cases are folded into one check:
      - the key is missing       -> query is None
      - the value is JSON null   -> query is None
      - the value is "   "       -> query.strip() is falsy
    """
    return bool(query and query.strip())


def clean_tickets(tickets):
    """
    Remove duplicates and unusable rows, then normalise the query text.

    Deduplication keeps the FIRST occurrence of each ticket_id, as specified.
    A set of seen IDs gives O(1) lookups and preserves input order, which a
    naive nested loop would not do efficiently.
    """
    seen_ids = set()
    cleaned = []

    for ticket in tickets:
        ticket_id = ticket.get("ticket_id")

        # 1. Drop repeats of an ID already kept.
        if ticket_id in seen_ids:
            continue

        # 2. Drop rows with no usable question. Note these are NOT added to
        #    seen_ids — a later, valid row with the same ID should still be
        #    eligible rather than silently discarded.
        query = ticket.get("query")
        if not is_valid_query(query):
            continue

        # 3. Normalise the text: strip tags first, then collapse the runs of
        #    whitespace that removing tags and newlines leaves behind.
        text = strip_html(query)
        text = " ".join(text.split())

        seen_ids.add(ticket_id)

        # Copy the original so the caller's input is not mutated, then
        # overwrite the query with its cleaned form.
        cleaned_ticket = dict(ticket)
        cleaned_ticket["query"] = text
        cleaned.append(cleaned_ticket)

    return cleaned


def simple_stem(word):
    """
    Reduce a word to a rough stem using suffix rules (bonus task).

    This is a deliberately small stemmer, not a linguistic one: it collapses
    the plural and participle forms that would otherwise be counted as
    separate keywords ("employees"/"employee", "flickering"/"flicker").

    The length guards stop it mangling short words — without the len check,
    "is" would become "i" and "days" would become "dai".
    """
    for suffix in ("ing", "ies", "es", "ed", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            stem = word[: -len(suffix)]
            # "ies" -> "y" reads better: "policies" -> "policy"
            if suffix == "ies":
                return stem + "y"
            return stem
    return word


def preprocess_text(text, apply_stemming=True):
    """
    Turn a cleaned query string into a list of meaningful tokens.

    Order matters here. Lowercasing happens before the punctuation regex
    because that pattern only covers a-z; doing it the other way round would
    leave every capital letter behind.

    Punctuation is replaced with a space rather than deleted, so "travel&meal"
    becomes two tokens instead of being fused into "travelmeal".
    """
    text = text.lower()
    text = NON_ALPHANUMERIC_PATTERN.sub(" ", text)

    tokens = text.split()
    tokens = [token for token in tokens if token not in STOP_WORDS]

    if apply_stemming:
        tokens = [simple_stem(token) for token in tokens]

    return tokens


def analyze_tickets(cleaned_tickets, top_n=5, output_path=OUTPUT_PATH):
    """
    Produce category counts and the most frequent keywords, and save results.

    Returns the summary dict so the function is testable and callers can use
    the numbers, rather than only printing them.
    """
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

    top_keywords = keyword_counts.most_common(top_n)

    # Ensure data/ exists so a fresh clone can run the script immediately.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)

    return {
        "total_valid_tickets": len(cleaned_tickets),
        "counts_per_category": dict(category_counts),
        "top_keywords": top_keywords,
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
