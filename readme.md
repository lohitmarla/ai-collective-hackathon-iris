# StudentConnect CT

**Tell us what you need. We'll help you find the student resources, support, opportunities, and events available around you.**

StudentConnect CT is a conversational resource finder scoped to UConn Hartford. It combines a manually curated starter directory with local search, Gemini-backed follow-up replies, category navigation, and links to live Connecticut event calendars. Without an API key, search and category browsing still work with a local fallback response.

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit. Create an API key in [Google AI Studio](https://aistudio.google.com/app/apikey), then set `GEMINI_API_KEY` in your environment or put it in `.streamlit/secrets.toml` as `GEMINI_API_KEY = "..."`. Streamlit does not load `.env` automatically. Without the key, local search and topic browsing remain available. `GEMINI_MODEL` defaults to `gemini-3.8-flash`.

## Demo searches

- “I'm stressed about money. What help is available?”
- “Where can I get free food?”
- “I need tutoring for math.”
- “I need mental health support.”
- “I'm looking for internships.”
- “I'm a new student and don't know what's available.”

## Project layout

```text
app.py                 Streamlit interface
data/resources.json    Curated resource directory (source of truth)
data/resources.csv     Spreadsheet-friendly copy of the directory
src/data_loader.py     Dataset loading and validation
src/search.py          Ranking, matching, and explanations
src/ai.py              Gemini intent expansion and grounded conversation
src/utils.py           Display helpers
tests/test_search.py   Search behavior tests
```

## Data and accuracy

The dataset is an intentionally small, manually curated starting point, not a comprehensive or live feed. Sources link to UConn Hartford Academic Resources & Student Services, Student Services, the Mental Health Resource Center, Academic Advising, Advocacy & Community Engagement, and 2-1-1 Connecticut. The pages are the authority for current hours, availability, appointments, eligibility, and service details; check them before relying on a listing. Cost and eligibility are labeled as variable where the source does not establish a universal answer. Update `last_verified` when reviewing a listing.

The CSV mirrors the JSON and is provided for review and editing. After editing the JSON, regenerate it with:

```bash
python -c "import csv,json; d=json.load(open('data/resources.json',encoding='utf-8')); f=open('data/resources.csv','w',newline='',encoding='utf-8-sig'); w=csv.DictWriter(f,fieldnames=d[0].keys()); w.writeheader(); [w.writerow({**r,'keywords':' | '.join(r['keywords'])}) for r in d]; f.close()"
```

## Search behavior

The local engine uses field-weighted TF-IDF cosine similarity together with exact keyword boosts and common synonym expansion. Names and categories receive more weight than keywords and descriptions. Corpus IDF statistics are cached in process and rebuilt when the resource dataset changes. Search explanations show the matching query or AI-expanded terms.

Retrieval is local-first: every message searches the curated JSON directory. If a match is weak, Gemini may expand the search terms; then Gemini can answer conversationally using current and prior local resource records as context. The app does not use AI to invent directory listings. Missing keys or API failures fall back to a local response. Category buttons filter the directory. The Current CT Events button opens live UConn Hartford, Hartford, and statewide event calendars so listings remain current. The app uses Google's `google-genai` Python SDK and the Gemini Interactions API. Gemini 3.8 Flash is the default model.

## Run checks

```bash
python -m unittest discover -s tests -v
```

## Safety and scope

This is a student resource directory, not an emergency service. For immediate danger call 911. StudentConnect CT does not provide diagnosis, eligibility decisions, or a guarantee that a service is currently available.
