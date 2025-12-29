from src.datacenter_layerA.normalize import md5_hash_string


def test_md5_deterministic():
    text = "Example Content"
    assert md5_hash_string(text) == md5_hash_string(text)
