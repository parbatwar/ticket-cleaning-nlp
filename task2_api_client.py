"""
Task 2: Fetch sample posts from a public REST API and reshape them into documents.

Handles network failures gracefully: if the request fails for any reason, a small
set of fallback documents is returned so downstream code keeps working.

Run:
    python task2_api_client.py
"""

import logging

import requests

API_URL = "https://jsonplaceholder.typicode.com/posts"
REQUEST_TIMEOUT = 10
POST_LIMIT = 5

FALLBACK_DOCUMENTS = [
    {
        "doc_id": 9001,
        "title": "Fallback document 1",
        "content": "Placeholder content used when the API is unreachable.",
        "word_count": 8,
    },
    {
        "doc_id": 9002,
        "title": "Fallback document 2",
        "content": "Second placeholder document so downstream code still has data.",
        "word_count": 9,
    },
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)


def to_document(post):
    """Reshape a raw API post into the document format required by the brief."""
    body = post["body"]
    return {
        "doc_id": post["id"],
        "title": post["title"].strip(),
        "content": body.replace("\n", " ").strip(),
        "word_count": len(body.split()),
    }


def fetch_documents(url=API_URL, timeout=REQUEST_TIMEOUT, limit=POST_LIMIT):
    """
    Fetch posts from the API and return them as documents.

    Returns FALLBACK_DOCUMENTS if the request fails for any reason.
    """
    logging.info("Requesting %s", url)

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        posts = response.json()
    except requests.exceptions.Timeout:
        logging.error("Request timed out after %s seconds", timeout)
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to %s", url)
    except requests.exceptions.RequestException as exc:
        logging.error("Request failed: %s", exc)
    except ValueError:
        logging.error("Response was not valid JSON")
    else:
        documents = [to_document(post) for post in posts[:limit]]
        logging.info("Received %d posts, returning %d documents", len(posts), len(documents))
        return documents

    logging.warning("Using %d fallback documents", len(FALLBACK_DOCUMENTS))
    return FALLBACK_DOCUMENTS


def main():
    documents = fetch_documents()

    print(f"\n{len(documents)} documents:\n")
    for document in documents:
        print(f"[{document['doc_id']}] {document['title']}")
        print(f"    {document['word_count']} words | {document['content'][:70]}...\n")


if __name__ == "__main__":
    main()
