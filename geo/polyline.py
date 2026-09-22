def decode(encoded: str, precision: int = 5) -> list[tuple[float, float]]:
    """Decode a Google-encoded polyline into (latitude, longitude) pairs."""
    scale = 10**precision
    points: list[tuple[float, float]] = []
    index = lat = lon = 0
    length = len(encoded)

    while index < length:
        value, index = _read_value(encoded, index)
        lat += value
        value, index = _read_value(encoded, index)
        lon += value
        points.append((lat / scale, lon / scale))

    return points


def _read_value(encoded: str, index: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        byte = ord(encoded[index]) - 63
        index += 1
        result |= (byte & 0x1F) << shift
        shift += 5
        if byte < 0x20:
            break
    value = ~(result >> 1) if result & 1 else result >> 1
    return value, index


def encode(points: list[tuple[float, float]], precision: int = 5) -> str:
    """Encode (latitude, longitude) pairs into a Google-encoded polyline."""
    scale = 10**precision
    output: list[str] = []
    previous_lat = previous_lon = 0

    for latitude, longitude in points:
        lat, lon = round(latitude * scale), round(longitude * scale)
        output.append(_write_value(lat - previous_lat))
        output.append(_write_value(lon - previous_lon))
        previous_lat, previous_lon = lat, lon

    return "".join(output)


def _write_value(value: int) -> str:
    value = ~(value << 1) if value < 0 else value << 1
    chunks = []
    while value >= 0x20:
        chunks.append(chr((0x20 | (value & 0x1F)) + 63))
        value >>= 5
    chunks.append(chr(value + 63))
    return "".join(chunks)
