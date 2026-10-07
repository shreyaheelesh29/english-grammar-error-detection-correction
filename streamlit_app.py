"""Streamlit interface for the local grammar checker."""

import streamlit as st

from nlp.analysis import document_stats, grammar_score, resolve_references
from nlp.correction import generate_correction
from nlp.checking import check_document
from nlp.ngram_model import get_model
from nlp.pos_tagger import get_pos_tags
from nlp.preprocessing import preprocess_text, split_sentences
from nlp.rewriter import generate_rewrites
from nlp.sentence_structure import analyze_structure
from nlp.tokenizer import tokenize

MAX_TEXT_CHARS = 20_000
SAMPLE_TEXT = "She go to college every day. They was happy, and after that they stopped to get something to eat"


@st.cache_resource
def load_nlp():
    """Use the trained English model when installed, otherwise keep the app self-contained."""
    try:
        import spacy
        try:
            return spacy.load("en_core_web_sm")
        except OSError:
            pipeline = spacy.blank("en")
            pipeline.add_pipe("sentencizer")
            return pipeline
    except ImportError:
        return None


def analyze_text(raw_text, goal):
    clean = preprocess_text(raw_text)
    if not clean:
        raise ValueError("Please enter some text to check.")
    if len(clean) > MAX_TEXT_CHARS:
        raise ValueError(f"Text is too long. The limit is {MAX_TEXT_CHARS:,} characters.")

    nlp = load_nlp()
    sentences = split_sentences(clean, nlp)
    tags_by_sentence = [get_pos_tags(sentence, nlp) for sentence in sentences]
    errors, grammar_engine = check_document(clean, sentences, tags_by_sentence)

    flattened_tags = [
        {**tag, "sentence_index": sentence_index}
        for sentence_index, tags in enumerate(tags_by_sentence)
        for tag in tags
    ]
    corrected = generate_correction(clean, errors)["corrected_text"]
    stats = document_stats(clean, flattened_tags)
    score = grammar_score(len(clean), len(sentences), errors)
    return {
        "original_text": clean,
        "corrected_text": corrected,
        "sentence_count": len(sentences),
        "word_count": sum(1 for token in tokenize(clean, nlp) if any(ch.isalnum() for ch in token["text"])),
        "error_count": len(errors),
        "errors": errors,
        "grammar_engine": grammar_engine,
        "pos_tags": flattened_tags,
        "sentences": sentences,
        "grammar_score": score,
        "stats": stats,
        "ngram": get_model().score_text(clean),
        "references": resolve_references(clean),
        "structure_issues": analyze_structure(sentences),
        "writing_alternatives": generate_rewrites(clean, goal),
        "nlp_mode": (
            "spaCy en_core_web_sm" if nlp is not None and "tagger" in nlp.pipe_names
            else "spaCy tokenizer + rule-based POS fallback"
        ),
    }


def show_findings(findings):
    if not findings:
        st.success("No supported grammar issues found in this text.")
        return
    for finding in findings:
        with st.expander(
            f"{finding.get('error_type', 'Writing issue')} · "
            f"{finding.get('rule_match_strength', 'rule match').title()}"
        ):
            st.write(finding.get("explanation", "Review this phrase."))
            col1, col2 = st.columns(2)
            col1.caption("Original")
            col1.code(finding.get("original", ""))
            col2.caption("Suggested")
            col2.code(finding.get("corrected", ""))


st.set_page_config(page_title="English Grammar Checker", page_icon="✍️", layout="wide")
st.title("✍️ English Grammar Checker")
st.write(
    "Check grammar, review suggested corrections, and explore "
    "the analysis. Writing is checked with a local LanguageTool engine when available."
)

with st.sidebar:
    st.header("Writing preferences")
    goal = st.selectbox("Suggestion style", ["general", "academic", "business", "casual"])
    st.caption("Style alternatives are optional. A limited rule-based checker is used if LanguageTool is unavailable.")

with st.form("grammar_check"):
    text = st.text_area(
        "Text to check", value=SAMPLE_TEXT, height=170, max_chars=MAX_TEXT_CHARS,
        placeholder="Paste a sentence or paragraph…",
    )
    submitted = st.form_submit_button("Check grammar", type="primary", width="stretch")

if submitted:
    st.session_state.pop("analysis", None)
    try:
        with st.spinner("Checking your text…"):
            analysis = analyze_text(text, goal)
            st.session_state["analysis"] = analysis
            st.session_state["corrected_text"] = analysis["corrected_text"]
    except ValueError as error:
        st.error(str(error))

result = st.session_state.get("analysis")
if result:
    score = result["grammar_score"]
    score_label = "Very Good" if score >= 90 else "Good" if score >= 80 else "Needs Improvement" if score >= 65 else "Major Corrections Needed"
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Grammar score", f"{score}/100", score_label)
    c2.metric("Issues found", result["error_count"])
    c3.metric("Words", result["word_count"])
    c4.metric("Sentences", result["sentence_count"])
    grammar_engine = result.get("grammar_engine", "Legacy result (engine not recorded)")
    st.caption(f"Grammar engine: {grammar_engine} · Analysis mode: {result['nlp_mode']}")

    corrections_tab, tags_tab, insights_tab, syntax_tab, wordnet_tab = st.tabs(
        ["Corrections", "POS tags", "Language insights", "Syntax parser", "WordNet"]
    )
    with corrections_tab:
        st.subheader("Suggested corrected text")
        st.session_state.setdefault("corrected_text", result["corrected_text"])
        st.text_area("Review and copy", height=130, key="corrected_text")
        st.subheader("Findings")
        show_findings(result["errors"])
        if result["writing_alternatives"]:
            st.subheader("Optional style alternatives")
            for alternative in result["writing_alternatives"]:
                st.markdown(f"**{alternative['label']}** — {alternative['reason']}")
                st.code(alternative["text"])
    with tags_tab:
        st.subheader("Part-of-speech tags")
        if result["pos_tags"]:
            st.dataframe(result["pos_tags"], width="stretch", hide_index=True)
        else:
            st.info("No words to tag.")
    with insights_tab:
        st.subheader("Document summary")
        st.json({key: value for key, value in result["stats"].items() if key != "pos_distribution"})
        st.caption("Part-of-speech distribution")
        if result["stats"]["pos_distribution"]:
            st.bar_chart(result["stats"]["pos_distribution"])
        with st.expander("N-gram scores and references"):
            st.json(result["ngram"])
            st.json(result["references"])
        if result["structure_issues"]:
            st.subheader("Sentence structure to review")
            st.json(result["structure_issues"])
    with syntax_tab:
        st.subheader("Small CFG / CYK demonstration")
        with st.form("parse_form"):
            parse_text = st.text_input("Sentence", value=result["original_text"])
            parse_submitted = st.form_submit_button("Parse sentence")
        if parse_submitted:
            from nlp.cyk_parser import parse
            parse_result = parse(preprocess_text(parse_text), load_nlp())
            if parse_result.get("accepted"):
                st.success("Accepted by the demo grammar.")
            else:
                st.info("This sentence is outside the demo grammar; that does not mean it is ungrammatical.")
            st.json(parse_result)
    with wordnet_tab:
        st.subheader("WordNet word lookup")
        with st.form("wordnet_form"):
            lookup_text = st.text_input("Words to look up", value=result["original_text"])
            lookup_submitted = st.form_submit_button("Look up words")
        if lookup_submitted:
            from nlp.semantics import analyze_words
            wordnet_result = analyze_words(lookup_text)
            if not wordnet_result["available"]:
                st.info(wordnet_result["note"])
            st.json(wordnet_result)

st.divider()
st.caption("Review suggested corrections in context. If LanguageTool is unavailable, the limited fallback may miss errors or flag text for review.")
