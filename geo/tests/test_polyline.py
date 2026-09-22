from geo.polyline import decode, encode

GOOGLE_EXAMPLE = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
GOOGLE_POINTS = [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]


def test_decode_google_reference_example():
    assert decode(GOOGLE_EXAMPLE) == GOOGLE_POINTS


def test_encode_google_reference_example():
    assert encode(GOOGLE_POINTS) == GOOGLE_EXAMPLE


def test_round_trip_with_precision_six():
    points = [(41.878113, -87.629799), (34.052235, -118.243683)]
    assert decode(encode(points, precision=6), precision=6) == points


def test_decode_empty_string():
    assert decode("") == []
