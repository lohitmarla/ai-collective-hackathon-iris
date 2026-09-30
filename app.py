"""StudentConnect CT: a conversational student resource finder."""
from pathlib import Path
import streamlit as st

from src.ai import extract_search_terms, generate_conversational_reply
from src.data_loader import load_resources
from src.search import needs_ai_expansion, search_resources
from src.utils import CATEGORY_ICONS

ROOT = Path(__file__).parent
st.set_page_config(page_title="StudentConnect CT", page_icon="🐾", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
.stApp {background:#f7f8fc;color:#19233b;font-family:'DM Sans',sans-serif}
.block-container {max-width:1120px;padding-top:2rem}
.hero {background:linear-gradient(120deg,#102550 0%,#174a72 60%,#257f83 100%);padding:2.7rem 3rem;border-radius:24px;color:white;margin:0 0 1.25rem;box-shadow:0 18px 45px #12304b22}
.hero h1 {color:white;font:800 2.5rem 'Manrope',sans-serif;letter-spacing:-1.5px;margin:0 0 .6rem}
.hero p {color:#e3f1f4;font-size:1.05rem;margin:.2rem 0;max-width:700px}
.eyebrow {color:#9ce0d5!important;text-transform:uppercase;letter-spacing:2px;font-size:.75rem!important;font-weight:700}
.resource {background:white;border:1px solid #e7eaf1;border-radius:18px;padding:1.2rem 1.35rem;margin:.55rem 0 1rem;box-shadow:0 5px 18px #1b34500b}
.resource h3 {font:700 1.15rem 'Manrope',sans-serif;margin:0;color:#172b48}
.tag {display:inline-block;background:#e9f4f3;color:#176a67;border-radius:30px;padding:.24rem .65rem;font-size:.77rem;font-weight:700;margin:.55rem .35rem .25rem 0}
.meta {font-size:.88rem;color:#566477;margin:.4rem 0}
.why {color:#334e68;background:#f4f8fb;border-left:3px solid #53aaa0;padding:.55rem .7rem;border-radius:0 8px 8px 0;font-size:.88rem}
div[data-testid="stChatInput"] textarea {border-radius:14px!important}
</style>
""", unsafe_allow_html=True)

resources = load_resources(ROOT / "data" / "resources.json")
categories = sorted({resource["category"] for resource in resources})
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "active_category" not in st.session_state:
    st.session_state.active_category = "All resources"

st.markdown(
    '<section class="hero"><p class="eyebrow">UConn Hartford · your campus, connected</p>'
    '<h1>Find your next step.</h1><p>Ask a question, follow up naturally, or choose a topic to explore campus support and Connecticut events.</p></section>',
    unsafe_allow_html=True,
)

st.markdown("#### Explore by topic")
nav_items = ["All resources", *categories, "Current CT events"]
for start in range(0, len(nav_items), 4):
    row = st.columns(4)
    for col, label in zip(row, nav_items[start:start + 4]):
        icon = "📅 " if label == "Current CT events" else ("✨ " if label == "All resources" else f"{CATEGORY_ICONS.get(label, '🔎')} ")
        if col.button(icon + label, key=f"nav_{label}", use_container_width=True,
                      type="primary" if st.session_state.active_category == label else "secondary"):
            st.session_state.active_category = label

active = st.session_state.active_category
if active == "Current CT events":
    st.markdown("### Current events in Connecticut")
    st.write("Open a live calendar to browse current listings. Check each organizer’s page for dates, registration, and changes.")
    event_sources = [
        ("UConn Hartford events", "https://events.uconn.edu/"),
        ("Connecticut events · CTVisit", "https://www.visitconnecticut.com/state/events/"),
        ("State of Connecticut events", "https://events.ct.gov/events"),
        ("Hartford events · Hartford Has It", "https://hartford.com/our-events/"),
    ]
    event_cols = st.columns(2)
    for index, (label, url) in enumerate(event_sources):
        event_cols[index % 2].link_button(label, url, use_container_width=True)
    st.divider()
else:
    selected_category = None if active == "All resources" else active
    if selected_category:
        st.markdown(f"### {CATEGORY_ICONS.get(selected_category, '🔎')} {selected_category}")
        st.caption("Showing this topic’s campus resources. Ask a follow-up below to narrow down your options.")
        category_results = search_resources("", resources)
        category_results = [entry for entry in category_results if entry["resource"]["category"] == selected_category]
        for entry in category_results:
            item = entry["resource"]
            st.markdown(
                f'''<article class="resource"><h3>{CATEGORY_ICONS.get(item["category"], "✨")} &nbsp;{item["name"]}</h3>
                <span class="tag">{item["category"]}</span><div class="meta">📍 {item["location"]} &nbsp; · &nbsp; 💵 {item["cost"]} &nbsp; · &nbsp; Eligibility: {item["eligibility"]}</div>
                <p>{item["description"]}</p><p><a href="{item["url"]}" target="_blank" rel="noopener noreferrer">Visit official resource ↗</a> &nbsp; <small>Source checked: {item["last_verified"]}</small></p></article>''',
                unsafe_allow_html=True,
            )

st.markdown("### Chat with StudentConnect")
st.caption("Ask about campus resources or follow up on a recommendation. Replies use the resource directory; current event listings are in the events tab.")

for turn_index, turn in enumerate(st.session_state.conversation):
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])
        if turn["role"] == "assistant":
            for entry in turn.get("matches", []):
                item = entry["resource"]
                st.markdown(
                    f'''<article class="resource"><h3>{CATEGORY_ICONS.get(item["category"], "✨")} &nbsp;{item["name"]}</h3>
                    <span class="tag">{item["category"]}</span><div class="meta">📍 {item["location"]} &nbsp; · &nbsp; 💵 {item["cost"]} &nbsp; · &nbsp; Eligibility: {item["eligibility"]}</div>
                    <p>{item["description"]}</p><div class="why"><b>Why it may help:</b> {entry["explanation"]}</div>
                    <p><a href="{item["url"]}" target="_blank" rel="noopener noreferrer">Visit official resource ↗</a> &nbsp; <small>Source checked: {item["last_verified"]}</small></p></article>''',
                    unsafe_allow_html=True,
                )

if not st.session_state.conversation:
    st.info("Try: ‘I’m stressed about money and need help paying for books’ or ‘What should I do if I can’t make an appointment?’")

query = st.chat_input("What would help right now?")
if query and query.strip():
    query = query.strip()
    prior_turns = list(st.session_state.conversation)
    st.session_state.conversation.append({"role": "user", "content": query})
    matches = search_resources(query, resources)
    if needs_ai_expansion(matches):
        terms = extract_search_terms(query)
        if terms:
            expanded = search_resources(query, resources, extra_terms=terms)
            if expanded and (not matches or expanded[0]["score"] > matches[0]["score"]):
                matches = expanded
    reply = generate_conversational_reply(query, prior_turns, matches)
    if not reply:
        if matches:
            reply = "I found a few campus resources that may help. I can narrow these down if you tell me what matters most, such as cost, location, or the kind of support you need."
        else:
            reply = "I can help with UConn Hartford student resources and point you to current Connecticut events. Tell me a little more about what support you’re looking for, or choose a topic above."
    st.session_state.conversation.append({"role": "assistant", "content": reply, "matches": matches[:5]})
    st.rerun()

st.divider()
st.caption("StudentConnect CT is a starting point, not an emergency service. If you or someone else is in immediate danger, call 911. Always check linked official pages for current hours, eligibility, and availability.")
