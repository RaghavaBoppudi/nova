from datetime import datetime
import pytz

# City/country to timezone mapping
TIMEZONE_MAP = {
    # United States
    "new york": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "houston": "America/Chicago",
    "phoenix": "America/Phoenix",
    "denver": "America/Denver",
    "seattle": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "miami": "America/New_York",
    "boston": "America/New_York",
    "atlanta": "America/New_York",
    "dallas": "America/Chicago",
    "las vegas": "America/Los_Angeles",

    # Europe
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "madrid": "Europe/Madrid",
    "rome": "Europe/Rome",
    "amsterdam": "Europe/Amsterdam",
    "zurich": "Europe/Zurich",
    "stockholm": "Europe/Stockholm",
    "oslo": "Europe/Oslo",
    "copenhagen": "Europe/Copenhagen",
    "helsinki": "Europe/Helsinki",
    "athens": "Europe/Athens",
    "lisbon": "Europe/Lisbon",
    "dublin": "Europe/Dublin",
    "moscow": "Europe/Moscow",

    # Asia
    "dubai": "Asia/Dubai",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "hyderabad": "Asia/Kolkata",
    "chennai": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata",
    "india": "Asia/Kolkata",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "tokyo": "Asia/Tokyo",
    "seoul": "Asia/Seoul",
    "singapore": "Asia/Singapore",
    "bangkok": "Asia/Bangkok",
    "jakarta": "Asia/Jakarta",
    "karachi": "Asia/Karachi",
    "islamabad": "Asia/Karachi",
    "lahore": "Asia/Karachi",
    "dhaka": "Asia/Dhaka",
    "kathmandu": "Asia/Kathmandu",
    "colombo": "Asia/Colombo",
    "tehran": "Asia/Tehran",
    "riyadh": "Asia/Riyadh",
    "baghdad": "Asia/Baghdad",
    "beirut": "Asia/Beirut",
    "tel aviv": "Asia/Jerusalem",
    "jerusalem": "Asia/Jerusalem",
    "taipei": "Asia/Taipei",
    "kuala lumpur": "Asia/Kuala_Lumpur",
    "manila": "Asia/Manila",

    # Australia / Pacific
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "brisbane": "Australia/Brisbane",
    "perth": "Australia/Perth",
    "auckland": "Pacific/Auckland",

    # Africa
    "cairo": "Africa/Cairo",
    "johannesburg": "Africa/Johannesburg",
    "nairobi": "Africa/Nairobi",
    "lagos": "Africa/Lagos",
    "casablanca": "Africa/Casablanca",

    # Americas
    "toronto": "America/Toronto",
    "vancouver": "America/Vancouver",
    "montreal": "America/Toronto",
    "mexico city": "America/Mexico_City",
    "sao paulo": "America/Sao_Paulo",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "bogota": "America/Bogota",
    "lima": "America/Lima",
    "santiago": "America/Santiago",

    # Timezone abbreviations
    "est": "America/New_York",
    "cst": "America/Chicago",
    "mst": "America/Denver",
    "pst": "America/Los_Angeles",
    "gmt": "GMT",
    "utc": "UTC",
    "ist": "Asia/Kolkata",
    "jst": "Asia/Tokyo",
    "cet": "Europe/Paris",
    "aest": "Australia/Sydney",
}


def get_time_in(location: str) -> str:
    """
    Get the current time in a given city, country, or timezone.
    Returns a natural language string.
    """
    location_lower = location.lower().strip()

    # Look up timezone
    tz_name = None
    for key, tz in TIMEZONE_MAP.items():
        if key in location_lower or location_lower in key:
            tz_name = tz
            break

    if not tz_name:
        return f"I don't have timezone information for {location}."

    try:
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)
        time_str = now.strftime("%I:%M %p")
        day_str = now.strftime("%A, %B %d")

        # Remove leading zero from hour
        time_str = time_str.lstrip("0")

        return f"It's {time_str} on {day_str} in {location.title()}."
    except Exception:
        return f"I couldn't get the time for {location}."


def is_midnight_in(location: str) -> str:
    """Check if it's currently midnight (or close to it) in a location."""
    location_lower = location.lower().strip()

    tz_name = None
    for key, tz in TIMEZONE_MAP.items():
        if key in location_lower or location_lower in key:
            tz_name = tz
            break

    if not tz_name:
        return f"I don't have timezone information for {location}."

    try:
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)
        hour = now.hour

        if hour == 0:
            return f"Yes, it's midnight in {location.title()} right now."
        elif hour == 23:
            return f"Almost midnight in {location.title()} — it's {now.strftime('%I:%M %p').lstrip('0')}."
        elif 1 <= hour <= 5:
            return f"Just past midnight in {location.title()} — it's {now.strftime('%I:%M %p').lstrip('0')}."
        else:
            return f"No, it's {now.strftime('%I:%M %p').lstrip('0')} in {location.title()}."
    except Exception:
        return f"I couldn't get the time for {location}."


def get_time_difference(location1: str, location2: str) -> str:
    """Get the time difference between two locations."""
    def get_tz(loc):
        loc_lower = loc.lower().strip()
        for key, tz in TIMEZONE_MAP.items():
            if key in loc_lower or loc_lower in key:
                return tz
        return None

    tz1_name = get_tz(location1)
    tz2_name = get_tz(location2)

    if not tz1_name:
        return f"I don't have timezone information for {location1}."
    if not tz2_name:
        return f"I don't have timezone information for {location2}."

    try:
        now = datetime.now(pytz.UTC)
        t1 = now.astimezone(pytz.timezone(tz1_name))
        t2 = now.astimezone(pytz.timezone(tz2_name))

        offset1 = t1.utcoffset().total_seconds() / 3600
        offset2 = t2.utcoffset().total_seconds() / 3600
        diff = abs(offset1 - offset2)

        hours = int(diff)
        minutes = int((diff - hours) * 60)

        if diff == 0:
            return f"{location1.title()} and {location2.title()} are in the same timezone."

        diff_str = f"{hours} hour{'s' if hours != 1 else ''}" if minutes == 0 else f"{hours} hour{'s' if hours != 1 else ''} and {minutes} minutes"

        if offset1 > offset2:
            return f"{location1.title()} is {diff_str} ahead of {location2.title()}."
        else:
            return f"{location2.title()} is {diff_str} ahead of {location1.title()}."
    except Exception:
        return "I couldn't calculate the time difference."