from app.utils.text import merge_overlap


def test_overlap_ignores_punctuation_and_case():
    assert merge_overlap("Hello world.", "world, welcome") == "Hello world. welcome"


def test_hindi_overlap():
    assert merge_overlap("आज मौसम अच्छा है", "अच्छा है hello") == "आज मौसम अच्छा है hello"


def test_no_overlap_preserves_text():
    assert merge_overlap("hello", "नमस्ते") == "hello नमस्ते"


def test_hindi_vowel_marks_are_not_discarded():
    assert merge_overlap("की", "कि") == "की कि"
