US_STATES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}

STATE_CODES_BY_NAME = {name.lower(): code for code, name in US_STATES.items()}

# (min_lat, max_lat, min_lon, max_lon) for the contiguous states, Alaska and Hawaii.
_US_BOUNDING_BOXES = (
    (24.4, 49.4, -125.0, -66.9),
    (51.0, 71.5, -179.9, -129.0),
    (18.9, 22.3, -160.3, -154.7),
)


def state_code(value: str) -> str | None:
    value = value.strip()
    if value.upper() in US_STATES:
        return value.upper()
    return STATE_CODES_BY_NAME.get(value.lower())


def is_within_us(latitude: float, longitude: float) -> bool:
    return any(
        min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon
        for min_lat, max_lat, min_lon, max_lon in _US_BOUNDING_BOXES
    )
