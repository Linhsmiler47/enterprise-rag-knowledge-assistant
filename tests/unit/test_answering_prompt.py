from enterprise_rag_knowledge_assistant.answering import SYSTEM_PROMPT


def test_system_prompt_treats_context_as_data_not_instructions() -> None:
    """ADR-0008 guardrail: retrieved document content must never be followed as a command."""
    lower = SYSTEM_PROMPT.lower()
    assert "data" in lower
    assert "never" in lower
    assert "instructions to follow" in lower or "not as something to obey" in lower


def test_system_prompt_refuses_to_reveal_itself() -> None:
    assert "never reveal" in SYSTEM_PROMPT.lower()
