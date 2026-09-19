from pathlib import Path

from spectraderm.rag.knowledge_base import (
    TOKEN_OVERLAP,
    TOKEN_TARGET,
    build_chunks,
    chunk_cleaned_text,
    load_sources,
)


APPROVED_URLS = {
    "https://www.medlineplus.gov/skinpigmentationdisorders.html",
    "https://www.medlineplus.gov/ency/article/003224.htm",
    "https://www.aad.org/public/everyday-care/skin-care-secrets/routine/fade-dark-spots",
    "https://www.aad.org/public/diseases/rosacea/what-is/symptoms",
    "https://www.aad.org/public/diseases/eczema/types/atopic-dermatitis/symptoms",
    "https://www.aad.org/public/diseases/acne/really-acne/symptoms",
    "https://www.nhs.uk/conditions/melanoma-skin-cancer/symptoms-of-melanoma-skin-cancer/",
}


def test_all_seven_approved_sources_are_registered_with_required_metadata():
    sources = load_sources()
    assert len(sources) == 7
    assert {source.url for source in sources} == APPROVED_URLS
    for source in sources:
        assert source.source_id and source.title and source.organization
        assert source.topic and source.category and source.retrieved_at


def test_source_ids_and_cleaned_text_are_nonempty_and_deterministic():
    first = load_sources()
    second = load_sources()
    assert first == second
    assert len({source.source_id for source in first}) == len(first)
    assert all(source.cleaned_text.strip() for source in first)


def test_chunks_are_nonempty_unique_and_keep_source_attribution():
    sources = {source.source_id: source for source in load_sources()}
    chunks = build_chunks()
    assert len(chunks) == 14
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    for chunk in chunks:
        source = sources[chunk.source_id]
        assert chunk.text.strip()
        assert chunk.chunk_id.startswith(f"{chunk.source_id}:chunk-")
        assert (chunk.title, chunk.organization, chunk.url, chunk.topic, chunk.category, chunk.retrieved_at) == (
            source.title, source.organization, source.url, source.topic, source.category, source.retrieved_at,
        )


def test_chunking_targets_size_and_retains_overlap_for_long_paragraphs():
    first = " ".join(f"first{i}" for i in range(300))
    second = " ".join(f"second{i}" for i in range(300))
    chunks = chunk_cleaned_text(f"## Example\n{first}\n{second}")
    assert len(chunks) == 2
    assert all(0 < len(text.split()) <= TOKEN_TARGET for _, text in chunks)
    assert chunks[0][1].split()[-TOKEN_OVERLAP:] == chunks[1][1].split()[:TOKEN_OVERLAP]


def test_chunk_ids_are_deterministic_and_scope_is_limited_to_approved_topics():
    first = build_chunks()
    second = build_chunks()
    assert first == second
    allowed_categories = {"appearance context", "limited common-condition context", "warning signs"}
    assert {source.category for source in load_sources()} <= allowed_categories
    assert all("estimated spectrum" not in chunk.text.lower() or "not" in chunk.text.lower() for chunk in first)


def test_cached_files_are_present_with_no_unapproved_source_documents():
    source_directory = Path("data/knowledge_base/sources")
    assert len(list(source_directory.glob("*.txt"))) == 7
