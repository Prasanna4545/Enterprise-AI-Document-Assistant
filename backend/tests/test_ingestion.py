from app.services.ingestion import DocumentIngestionService, ParsedPage


def test_chunking_preserves_page_metadata():
    pages = [
        ParsedPage(page_number=1, text="This is the first page of the corporate policy manual with important rules."),
        ParsedPage(page_number=2, text="This is page two containing remote work guidelines and security protocols.")
    ]

    chunks = DocumentIngestionService.chunk_text(pages, chunk_size_tokens=20, overlap_tokens=5)
    
    assert len(chunks) >= 2
    assert chunks[0].page_number == 1
    assert "first page" in chunks[0].content
    assert chunks[-1].page_number == 2
    assert "page two" in chunks[-1].content
