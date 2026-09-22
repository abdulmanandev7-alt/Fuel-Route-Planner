from geo.us import is_within_us, state_code


def test_state_code_accepts_abbreviations_and_names():
    assert state_code("il") == "IL"
    assert state_code("Illinois") == "IL"
    assert state_code(" new york ") == "NY"
    assert state_code("ZZ") is None
    assert state_code("Ontario") is None


def test_is_within_us():
    assert is_within_us(41.8781, -87.6298)
    assert is_within_us(61.2181, -149.9003)
    assert is_within_us(21.3069, -157.8583)
    assert not is_within_us(19.4326, -99.1332)
    assert not is_within_us(51.5074, -0.1278)
