"""Task 10 - Multi-agent generation with citations.

If XAH_API_KEY is configured, this module runs a small multi-agent RAG workflow
against the third-party OpenAI-compatible chat endpoint. Without an API key it
falls back to extractive generation so the project still runs offline and tests
remain deterministic.
"""

import os

import requests
from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve

load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

XAH_API_URL = os.getenv("XAH_API_URL", "https://api.xah.io/v1/chat/completions")
XAH_API_KEY = os.getenv("XAH_API_KEY", "")
XAH_MODEL = os.getenv("XAH_MODEL", "vuduongcalvin/gemini-3.1-flash-lite")

SYSTEM_PROMPT = """Bạn là trợ lý RAG trả lời bằng tiếng Việt về pháp luật ma túy
và tin tức báo chí liên quan. Chỉ dùng thông tin trong CONTEXT.

Quy tắc bắt buộc:
- Mọi nhận định/sự kiện phải có citation ngay sau câu, dạng [Nguồn, năm].
- Nếu CONTEXT không đủ bằng chứng, nói: "Tôi không thể xác minh thông tin này từ nguồn hiện có."
- Không bịa điều luật, ngày tháng, tên người, mức phạt.
- Trả lời gọn, rõ, ưu tiên trực tiếp vào câu hỏi."""

PLANNER_PROMPT = SYSTEM_PROMPT + """

Vai trò agent: Evidence Planner.
Nhiệm vụ:
- Xác định ý chính cần trả lời.
- Chọn các document liên quan nhất trong CONTEXT.
- Viết gạch đầu dòng ngắn, mỗi gạch đầu dòng kết thúc bằng citation [Nguồn, năm].
- Nếu không đủ bằng chứng, nói rõ điểm nào không xác minh được."""

DRAFTER_PROMPT = SYSTEM_PROMPT + """

Vai trò agent: Answer Writer.
Nhiệm vụ:
- Viết câu trả lời cuối cùng bằng tiếng Việt dựa trên CONTEXT và EVIDENCE_PLAN.
- Mỗi câu có thông tin thực tế phải có citation.
- Không nhắc tới tên agent hoặc quy trình nội bộ."""

VERIFIER_PROMPT = SYSTEM_PROMPT + """

Vai trò agent: Citation Verifier.
Nhiệm vụ:
- Kiểm tra ANSWER_DRAFT so với CONTEXT.
- Giữ lại các ý đúng, sửa hoặc loại bỏ ý không có bằng chứng.
- Đảm bảo câu trả lời cuối cùng có citation đúng định dạng [Nguồn, năm].
- Chỉ trả về câu trả lời cuối cùng, không trả về nhận xét kiểm tra."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    if len(chunks) <= 2:
        return chunks
    reordered = [chunks[0]]
    middle = chunks[2::2]
    tail = list(reversed(chunks[1::2]))
    return reordered + middle + tail


def _citation_label(chunk: dict, index: int) -> str:
    metadata = chunk.get("metadata", {})
    source = metadata.get("source") or metadata.get("path") or f"Source {index}"
    year = metadata.get("year")
    if not year:
        text = f"{source} {chunk.get('content', '')}"
        for candidate in ("2026", "2025", "2024", "2023", "2022", "2021", "2015"):
            if candidate in text:
                year = candidate
                break
    return f"{source}, {year or 'n.d.'}"


def format_context(chunks: list[dict]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        source = metadata.get("source", f"Source {index}")
        doc_type = metadata.get("type", "unknown")
        parts.append(
            f"[Document {index} | Source: {source} | Type: {doc_type} | "
            f"Score: {float(chunk.get('score', 0.0)):.3f}]\n{chunk.get('content', '')}"
        )
    return "\n\n---\n\n".join(parts)


def _build_user_prompt(
    query: str,
    context: str,
    history: list[dict] | None = None,
    extra_sections: dict[str, str] | None = None,
) -> str:
    history_text = ""
    if history:
        turns = []
        for item in history[-6:]:
            role = item.get("role", "user")
            content = item.get("content", "")
            if content:
                turns.append(f"{role}: {content}")
        history_text = "\n".join(turns)

    extra_text = ""
    if extra_sections:
        extra_text = "\n\n".join(
            f"{name.upper()}:\n{value}" for name, value in extra_sections.items() if value
        )

    prompt = (
        f"CONVERSATION_HISTORY:\n{history_text or '(none)'}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION:\n{query}\n\n"
    )
    if extra_text:
        prompt += f"{extra_text}\n\n"
    return prompt + "Hãy trả lời dựa trên CONTEXT và luôn kèm citation."


def _call_chat_model(
    query: str,
    context: str,
    history: list[dict] | None = None,
    system_prompt: str = SYSTEM_PROMPT,
    extra_sections: dict[str, str] | None = None,
) -> str | None:
    if not XAH_API_KEY:
        return None

    payload = {
        "model": XAH_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": _build_user_prompt(query, context, history, extra_sections),
            },
        ],
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
    }
    headers = {
        "Authorization": f"Bearer {XAH_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.post(XAH_API_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def _run_multi_agent_generation(
    query: str,
    context: str,
    history: list[dict] | None = None,
) -> dict | None:
    """Run planner -> drafter -> verifier agents over the same retrieved context."""
    evidence_plan = _call_chat_model(
        query,
        context,
        history=history,
        system_prompt=PLANNER_PROMPT,
    )
    if not evidence_plan:
        return None

    draft = _call_chat_model(
        query,
        context,
        history=history,
        system_prompt=DRAFTER_PROMPT,
        extra_sections={"evidence_plan": evidence_plan},
    )
    if not draft:
        return None

    final_answer = _call_chat_model(
        query,
        context,
        history=history,
        system_prompt=VERIFIER_PROMPT,
        extra_sections={"evidence_plan": evidence_plan, "answer_draft": draft},
    )
    if not final_answer:
        return None

    return {
        "answer": final_answer,
        "agent_trace": {
            "planner": evidence_plan,
            "drafter": draft,
            "verifier": final_answer,
        },
    }


def _first_sentences(text: str, max_sentences: int = 2) -> str:
    separators = [". ", "\n"]
    sentences = [text.strip()]
    for separator in separators:
        if separator in text:
            sentences = [part.strip() for part in text.split(separator) if part.strip()]
            break
    return ". ".join(sentences[:max_sentences]).strip()


def generate_with_citation(
    query: str,
    top_k: int = TOP_K,
    history: list[dict] | None = None,
    use_llm: bool = True,
) -> dict:
    chunks = retrieve(query, top_k=top_k)
    reordered = reorder_for_llm(chunks)
    if not reordered:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_source": "none",
            "context": "",
            "used_llm": False,
            "generation_mode": "no_context",
            "agent_trace": None,
            "api_error": None,
        }

    context = format_context(reordered)
    agent_result = None
    api_error = None
    if use_llm:
        try:
            agent_result = _run_multi_agent_generation(query, context, history)
        except Exception as exc:
            agent_result = None
            api_error = str(exc)
            print(f"Multi-agent LLM call failed, using extractive fallback: {exc}")

    if agent_result:
        return {
            "answer": agent_result["answer"],
            "sources": chunks,
            "retrieval_source": chunks[0].get("source", "hybrid") if chunks else "none",
            "context": context,
            "used_llm": True,
            "generation_mode": "multi_agent",
            "agent_trace": agent_result["agent_trace"],
            "api_error": None,
        }

    answer_parts = []
    for index, chunk in enumerate(reordered[: min(3, len(reordered))], 1):
        evidence = _first_sentences(chunk.get("content", ""), max_sentences=2)
        if evidence:
            answer_parts.append(f"{evidence} [{_citation_label(chunk, index)}]")

    answer = " ".join(answer_parts).strip()
    if not answer:
        answer = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": chunks[0].get("source", "hybrid") if chunks else "none",
        "context": context,
        "used_llm": False,
        "generation_mode": "extractive_fallback",
        "agent_trace": None,
        "api_error": api_error,
    }


if __name__ == "__main__":
    print(generate_with_citation("Hinh phat tang tru ma tuy?")["answer"])
