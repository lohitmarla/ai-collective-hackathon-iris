"""Local-first resource retrieval with cached TF-IDF corpus statistics."""
from functools import lru_cache
import json
import math
import re
from collections import Counter

STOP_WORDS = {"i", "me", "my", "a", "an", "the", "to", "for", "of", "and", "or", "is", "are", "what", "where", "can", "do", "need", "please", "with", "about", "some", "help", "get", "find", "available", "looking", "am", "this", "that", "it"}
SYNONYMS = {
    "food": {"hungry", "meal", "meals", "eat", "pantry", "grocery"},
    "mental health": {"stress", "stressed", "anxiety", "anxious", "depressed", "counseling", "therapy", "wellness"},
    "career": {"job", "jobs", "internship", "internships", "employment", "resume", "work"},
    "tutoring": {"tutor", "tutors", "math", "writing", "study", "academic", "course"},
    "financial": {"money", "cost", "bill", "bills", "financial", "scholarship", "tuition", "emergency"},
    "community": {"event", "events", "friends", "club", "clubs", "belong", "connect", "social"},
}

def tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.casefold()) if w not in STOP_WORDS and len(w) > 1]

def _document_tokens(resource: dict) -> list[str]:
    """Give names/categories/keywords extra influence over long descriptions."""
    tokens = tokenize(resource["name"]) * 3
    tokens += tokenize(resource["category"]) * 2
    tokens += tokenize(" ".join(resource.get("keywords", []))) * 2
    tokens += tokenize(resource["description"])
    return tokens

@lru_cache(maxsize=8)
def _tfidf_index(serialized_resources: str):
    """Build document vectors once per dataset version, then reuse them."""
    resources = json.loads(serialized_resources)
    token_docs = [_document_tokens(resource) for resource in resources]
    document_frequency = Counter(term for terms in token_docs for term in set(terms))
    count = len(token_docs)
    vectors = []
    for tokens in token_docs:
        frequencies = Counter(tokens)
        vector = {
            term: (1 + math.log(freq)) * (math.log((count + 1) / (document_frequency[term] + 1)) + 1)
            for term, freq in frequencies.items()
        }
        norm = math.sqrt(sum(weight * weight for weight in vector.values())) or 1.0
        vectors.append({term: weight / norm for term, weight in vector.items()})
    return resources, token_docs, document_frequency, vectors

def search_resources(query: str, resources: list[dict], extra_terms: list[str] | None = None) -> list[dict]:
    """Rank local resources with field-weighted TF-IDF plus exact-match boosts.

    ``extra_terms`` may contain AI-extracted intent keywords. No remote resource
    search happens here; all candidates remain in the supplied local dataset.
    """
    serialized = json.dumps(resources, sort_keys=True, ensure_ascii=False)
    indexed_resources, token_docs, document_frequency, vectors = _tfidf_index(serialized)
    original_terms = set(tokenize(query))
    intent_terms = set(tokenize(" ".join(extra_terms or []))) - original_terms
    expanded = original_terms | intent_terms
    for group, synonyms in SYNONYMS.items():
        group_terms = set(tokenize(group)) | synonyms
        if expanded & group_terms:
            expanded |= group_terms

    query_weights = {term: 2.0 for term in original_terms}
    for term in expanded - original_terms:
        query_weights[term] = 0.45 if term in intent_terms else 0.3
    if query_weights:
        query_weights = {
            term: weight * (math.log((len(indexed_resources) + 1) / (document_frequency.get(term, 0) + 1)) + 1)
            for term, weight in query_weights.items()
        }
        query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values())) or 1.0
        query_weights = {term: weight / query_norm for term, weight in query_weights.items()}

    ranked = []
    for index, resource in enumerate(indexed_resources):
        fields = {
            "name": set(tokenize(resource["name"])),
            "category": set(tokenize(resource["category"])),
            "keywords": set(tokenize(" ".join(resource.get("keywords", [])))),
            "description": set(tokenize(resource["description"])),
        }
        lexical_score = 0.0
        matched = set()
        for term in expanded:
            field_weight = max(
                5 if term in fields["name"] else 0,
                4 if term in fields["category"] else 0,
                3 if term in fields["keywords"] else 0,
                1 if term in fields["description"] else 0,
            )
            if field_weight:
                lexical_score += field_weight * (1.0 if term in original_terms else 0.35)
                matched.add(term)
        cosine = sum(weight * vectors[index].get(term, 0.0) for term, weight in query_weights.items())
        score = lexical_score + cosine * 4.0
        if not query_weights or score > 0:
            original_matches = sorted(matched & original_terms)
            intent_matches = sorted(matched & intent_terms)
            if not expanded:
                explanation = "A helpful starting point for this topic."
            elif original_matches:
                explanation = "Matches your words: " + ", ".join(original_matches)
            elif intent_matches:
                explanation = "AI identified related needs: " + ", ".join(intent_matches)
            else:
                explanation = "Related based on similar resource topics."
            ranked.append({"resource": resource, "score": score, "tfidf_score": cosine, "explanation": explanation})
    return sorted(ranked, key=lambda entry: (-entry["score"], entry["resource"]["name"].casefold()))

def needs_ai_expansion(results: list[dict], weak_match_threshold: float = 1.5) -> bool:
    """Recommend intent extraction only when local retrieval has no strong hit."""
    return not results or results[0]["score"] < weak_match_threshold
