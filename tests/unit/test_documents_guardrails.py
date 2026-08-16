from enterprise_rag_knowledge_assistant.api.routes.documents import (
    _extension_of,
    _sanitize_display_filename,
)


def test_sanitize_strips_directory_components() -> None:
    assert _sanitize_display_filename("../../etc/passwd") == "passwd"
    assert _sanitize_display_filename("/etc/shadow") == "shadow"


def test_sanitize_falls_back_to_upload_for_empty_name() -> None:
    assert _sanitize_display_filename("") == "upload"
    assert _sanitize_display_filename("   ") == "upload"


def test_sanitize_strips_control_characters() -> None:
    assert _sanitize_display_filename("notes\x00.md") == "notes.md"


def test_extension_of_is_case_insensitive() -> None:
    assert _extension_of("Policy.MD") == ".md"
    assert _extension_of("notes.txt") == ".txt"
    assert _extension_of("archive.tar.gz") == ".gz"
    assert _extension_of("no-extension") == ""
