def thumbnail_width() -> int:
    return 320


def test_thumbnail_is_320_pixels_wide() -> None:
    assert thumbnail_width() == 320
