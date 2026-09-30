"""Load and validate the hand-curated resource dataset."""
import json
from pathlib import Path

REQUIRED = {"id", "name", "category", "description", "url", "cost", "eligibility", "location", "keywords", "last_verified"}

def load_resources(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as source:
        records = json.load(source)
    if not isinstance(records, list):
        raise ValueError("Resource data must be a JSON list")
    ids = set()
    for record in records:
        missing = REQUIRED - record.keys()
        if missing:
            raise ValueError(f"Resource missing fields: {', '.join(sorted(missing))}")
        if record["id"] in ids:
            raise ValueError(f"Duplicate resource id: {record['id']}")
        ids.add(record["id"])
    return records
