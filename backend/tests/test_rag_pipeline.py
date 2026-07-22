from app.services.rag_pipeline import RAGPipelineService


def test_build_prompt_includes_context_and_citations():
    query = "What is the annual leave allowance?"
    chunks = [
        {
            "document_id": "doc-1",
            "title": "Employee Handbook",
            "filename": "handbook.pdf",
            "page_number": 5,
            "content": "Full-time employees receive 25 days of paid annual leave per calendar year."
        }
    ]

    prompt = RAGPipelineService.build_prompt(query, chunks)

    assert "handbook.pdf" in prompt
    assert "Page: 5" in prompt
    assert "25 days of paid annual leave" in prompt
    assert query in prompt
