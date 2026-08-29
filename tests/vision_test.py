from backend.tools.media import image_to_data_url


def test_image_data_url(tmp_path):
    p = tmp_path / "tiny.png"
    # 1x1 PNG
    p.write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
        )
    )
    url = image_to_data_url(str(p))
    assert url.startswith("data:image/png;base64,")
