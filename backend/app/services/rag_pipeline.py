import json
import asyncio
from typing import List, Dict, Any, AsyncGenerator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an Enterprise AI Document Assistant for an organization.
Your primary job is to answer user queries clearly, accurately, and professionally based ONLY on the provided Context Chunks from uploaded company documents.

STRICT RULES:
1. Base your answer STRICTLY on the facts provided in the Context Chunks below. Do NOT make up information or introduce outside facts not supported by the context.
2. If the answer cannot be found in the context, state clearly: "Based on the provided documents, I could not find information regarding this question."
3. Include explicit source citations in your response referencing the document filename and page number when citing facts, e.g., `(Source: HR_Policy.pdf, Page 3)`.
4. Be clear, concise, and structure your answer using Markdown (bullet points, headings, bold text) for optimal readability.
"""


class RAGPipelineService:
    @staticmethod
    def build_prompt(query: str, chunks: List[Dict[str, Any]], chat_history: List[Dict[str, str]] = None) -> str:
        """Assembles prompt with context chunks and citation tags."""
        context_str = ""
        if not chunks:
            context_str = "No relevant document chunks were found for this query."
        else:
            for idx, c in enumerate(chunks):
                doc_title = c.get("title", "Document")
                filename = c.get("filename", "document.pdf")
                page_num = c.get("page_number", 1)
                content = c.get("content", "").strip()

                context_str += f"\n--- CHUNK {idx + 1} | File: {filename} | Page: {page_num} | Title: {doc_title} ---\n{content}\n"

        prompt = f"### CONTEXT DOCUMENTS:\n{context_str}\n\n"

        if chat_history:
            prompt += "### RECENT CONVERSATION:\n"
            for msg in chat_history[-4:]:  # last 4 messages for multi-turn context
                role = "User" if msg["sender"] == "USER" else "Assistant"
                prompt += f"{role}: {msg['content']}\n"
            prompt += "\n"

        prompt += f"### USER QUERY:\n{query}\n\n### ASSISTANT ANSWER:"
        return prompt

    @staticmethod
    async def stream_rag_response(
        query: str,
        chunks: List[Dict[str, Any]],
        chat_history: List[Dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streams response tokens as Server-Sent Events (SSE JSON lines)
        followed by a final citations payload.
        """
        prompt = RAGPipelineService.build_prompt(query, chunks, chat_history)

        citations_payload = []
        for c in chunks:
            citations_payload.append({
                "chunk_id": c.get("chunk_id"),
                "document_id": c.get("document_id"),
                "filename": c.get("filename"),
                "title": c.get("title"),
                "page_number": c.get("page_number"),
                "snippet": c.get("content")[:150] + "..." if len(c.get("content", "")) > 150 else c.get("content")
            })


        # Try Anthropic API if valid key is available
        if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY != "mock-anthropic-key":
            try:
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                
                async with client.messages.stream(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1500,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}]
                ) as stream:
                    async for text in stream.text_stream:
                        evt_data = json.dumps({"type": "content", "text": text})
                        yield f"data: {evt_data}\n\n"

                # Send citations at the end of stream
                evt_citations = json.dumps({"type": "citations", "citations": citations_payload})
                yield f"data: {evt_citations}\n\n"
                return

            except Exception as e:
                logger.warning(f"Anthropic API stream error: {e}. Falling back to mock generator.")

        # Fallback generator if no key or error
        if not chunks:
            fallback_text = "Based on the provided documents, I could not find any relevant information regarding your query. Please upload pertinent documents or rephrase your question."
        else:
            top_file = chunks[0].get("filename", "document.pdf")
            page_num = chunks[0].get("page_number", 1)
            fallback_text = (
                f"Based on **{top_file}** (Page {page_num}), here is the relevant information regarding your query:\n\n"
                f"> \"{chunks[0].get('content', '')[:250]}...\"\n\n"
                f"Key points summarized from your uploaded document:\n"
                f"- Document referenced: **{chunks[0].get('title', 'Company Doc')}**\n"
                f"- Page number: `{page_num}`\n"
                f"- Total context chunks retrieved: `{len(chunks)}`\n\n"
                f"*(Source citation: {top_file}, Page {page_num})*"
            )

        # Simulate smooth streaming token by token
        words = fallback_text.split(" ")
        for i in range(0, len(words), 3):
            chunk_str = " ".join(words[i:i+3]) + " "
            evt_data = json.dumps({"type": "content", "text": chunk_str})
            yield f"data: {evt_data}\n\n"
            await asyncio.sleep(0.04)

        evt_citations = json.dumps({"type": "citations", "citations": citations_payload})
        yield f"data: {evt_citations}\n\n"
