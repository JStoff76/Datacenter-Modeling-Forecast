from src.datacenter_layerA.extract import extract_from_text


SAMPLE_TEXT = """
The new facility will provide 150,000 square feet of space and deliver 30 MW of critical power.
It supports 1200 racks with an average of 12 kW / rack using liquid cooled design.
Phase one go-live expected in Jan 2025.
"""


def test_extract_detects_multiple_specs():
    obs = extract_from_text("dc1", SAMPLE_TEXT, "http://example.com", 0.8)
    names = {o.spec_name for o in obs}
    assert "square_ft" in names
    assert "power_mw" in names
    assert "rack_count" in names
    assert any(o.spec_name == "kw_per_rack" for o in obs)
    assert any(o.spec_name == "cooling_type" for o in obs)
