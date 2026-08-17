from app.services.text_extraction import extract_text_from_bytes


def test_extract_text_from_txt_bytes():
    text = extract_text_from_bytes("resume.txt", b"Python FastAPI Docker resume")

    assert "Python" in text
