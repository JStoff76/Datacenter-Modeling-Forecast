from src.datacenter_layerA.normalize import normalize_text


def test_normalize_text_collapses_whitespace_and_punctuation():
    raw = "  Data  Center\nName!! "
    assert normalize_text(raw) == "data center name"
