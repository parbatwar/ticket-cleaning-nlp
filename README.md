# Ticket Cleaning & NLP — TechKraft AI Intern Take-Home

Submission for the TechKraft Inc AI Intern pre-hiring assignment.

- **Part 1** — cleaning noisy helpdesk tickets and basic NLP preprocessing
- **Part 2** — calling a public REST API with error handling and a fallback
- **Part 3** — written answers on prompt engineering, RAG chunking and AI safety, in [`ANSWERS.md`](ANSWERS.md)

## Project structure

```
.
├── data/
│   ├── support_tickets.json      input dataset (provided in the brief)
│   └── cleaned_tickets.json      output of Part 1, committed so results are visible
├── task1_nlp_cleaner.py          Part 1
├── task2_api_client.py           Part 2
├── ANSWERS.md                    Part 3
├── requirements.txt
└── .gitignore
```

## Setup

Developed on Python 3.14; requires Python 3.8 or newer.

**1. Clone the repository**

```bash
git clone https://github.com/parbatwar/ticket-cleaning-nlp.git
cd ticket-cleaning-nlp
```

**2. Create and activate a virtual environment**

Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

Only Part 2 has a dependency (`requests`). Part 1 uses the standard library only.

## Running the scripts

### Part 1

```bash
python task1_nlp_cleaner.py
```

Reads `data/support_tickets.json`, removes duplicate and unusable tickets, tokenises
the remaining queries, prints a summary, and writes `data/cleaned_tickets.json`.

```
Loaded 9 raw tickets
Kept 6 after cleaning

Tickets per category:
  Finance    1
  HR         2
  IT         3

Top 5 keywords:
  1. vpn             2
  2. day             2
  3. reset           1
  4. password        1
  5. urgent          1
```

Three tickets are dropped: one duplicate `T-101`, one whitespace-only query
(`T-104`) and one `null` query (`T-106`).

### Part 2

```bash
python task2_api_client.py
```

Fetches posts from `https://jsonplaceholder.typicode.com/posts`, reshapes the
first five into the required document format, and prints them.

```
22:25:37 | INFO     | Requesting https://jsonplaceholder.typicode.com/posts
22:25:37 | INFO     | Received 100 posts, returning 5 documents
```

On failure it logs the cause and returns two fallback documents instead:

```
22:25:45 | ERROR    | Could not connect to https://this-host-does-not-exist-12345.com/posts
22:25:45 | WARNING  | Using 2 fallback documents
```

## Design notes and assumptions

**Part 1**

- The stop-word list is taken verbatim from the brief rather than from a library,
  so the output is reproducible against the specification.
- Stemming (the optional bonus) uses simple suffix rules rather than NLTK or
  spaCy, keeping Part 1 free of third-party dependencies. Length guards stop
  over-stemming short words — without them, `days` becomes `dai`. The `es` rule
  applies only after a sibilant (`boxes` → `box`, `dishes` → `dish`); elsewhere
  the plural marker is just `s`, so `employees` → `employee`.
- Invalid tickets are skipped **without** their `ticket_id` being recorded as
  seen. If the same ID later appeared with a valid query, that row would still be
  kept rather than discarded as a duplicate.
- `Wi-Fi` tokenises to `wi` and `fi`, because the brief specifies keeping only
  alphanumeric words. A production pipeline would likely preserve hyphenated
  technical terms.
- Punctuation is replaced with a space rather than deleted, so `travel&meal`
  splits into two tokens instead of fusing into one.
- `cleaned_tickets.json` is committed rather than ignored, so the output can be
  inspected without running the script.

**Part 2**

- Exception handlers are ordered specific-to-general. `Timeout` and
  `ConnectionError` are subclasses of `RequestException`, so the general handler
  is last; otherwise it would catch everything and the specific messages would
  never appear.
- `ValueError` is caught in addition to the exceptions named in the brief, because
  `response.json()` raises it when the body is not valid JSON — for example when
  a server returns an HTML error page. The fallback exists so downstream code
  never crashes, and this is another way it could.
- The success path sits in the `try`/`else` block rather than inside `try`, so a
  bug in `to_document()` surfaces as a real error instead of being misreported as
  a network failure.
- `fetch_documents()` takes `url`, `timeout` and `limit` as parameters defaulting
  to the module constants, which made the failure paths testable without editing
  the file.

## Challenges and testing

**Testing the failure paths.** The brief asks for a fallback when the API is
unreachable. Rather than disconnecting from the network, each failure was
triggered directly by overriding the defaults:

```python
from task2_api_client import fetch_documents

fetch_documents(url="https://jsonplaceholder.typicode.com/nope")          # 404 -> HTTPError
fetch_documents(url="https://this-host-does-not-exist-12345.com/posts")   # ConnectionError
fetch_documents(timeout=0.001)                                            # Timeout
```

All three log a distinct error and return the two fallback documents.

**A 404 is not an exception.** `requests.get()` does not raise on a non-200
response — the request succeeded, the answer was simply an error code. Without
`response.raise_for_status()` the script would continue and attempt to parse an
error page as JSON. This is the easiest failure in Part 2 to miss.

**Deciding how far to go with stemming.** Full lemmatisation needs NLTK or spaCy
and a model download, which felt disproportionate for a dataset of nine tickets
and would have added setup steps for anyone running this. Suffix rules handle the
plurals and participles present in the data at the cost of being linguistically
crude.

**A bug found while documenting.** The first version of the stemmer stripped `es`
from any word ending in it, so `employees` became `employe` while `employee` was
left unchanged — the two never unified, which defeats the purpose of stemming.
Restricting the `es` rule to words whose stem ends in a sibilant fixed it. The
lesson was that writing down what the code *should* do is a reasonable way to
find out what it actually does; the bug was invisible in the output because
`employees` appears only once in the dataset.
