import pint

ureg = pint.UnitRegistry()


# Natural language alias map for units Pint doesn't recognize
UNIT_ALIASES = {
    # Length
    "feet": "foot",
    "ft": "foot",
    "inches": "inch",
    "in": "inch",
    "yards": "yard",
    "yd": "yard",
    "miles": "mile",
    "mi": "mile",
    "kilometers": "kilometer",
    "km": "kilometer",
    "meters": "meter",
    "m": "meter",
    "centimeters": "centimeter",
    "cm": "centimeter",
    "millimeters": "millimeter",
    "mm": "millimeter",

    # Weight
    "pounds": "pound",
    "lbs": "pound",
    "lb": "pound",
    "ounces": "ounce",
    "oz": "ounce",
    "kilograms": "kilogram",
    "kg": "kilogram",
    "grams": "gram",
    "g": "gram",
    "tonnes": "metric_ton",
    "tons": "metric_ton",

    # Temperature (handled separately)
    "celsius": "degC",
    "centigrade": "degC",
    "fahrenheit": "degF",
    "kelvin": "kelvin",

    # Volume
    "liters": "liter",
    "litres": "liter",
    "l": "liter",
    "milliliters": "milliliter",
    "ml": "milliliter",
    "gallons": "gallon",
    "gal": "gallon",
    "pints": "pint",
    "pt": "pint",
    "cups": "cup",
    "fluid ounces": "fluid_ounce",
    "fl oz": "fluid_ounce",

    # Speed
    "mph": "mile / hour",
    "kph": "kilometer / hour",
    "kmh": "kilometer / hour",
    "km/h": "kilometer / hour",
    "m/s": "meter / second",
    "knots": "knot",

    # Area
    "square feet": "foot ** 2",
    "sq ft": "foot ** 2",
    "square meters": "meter ** 2",
    "sq m": "meter ** 2",
    "acres": "acre",
    "hectares": "hectare",

    # Data (binary — 1024-based)
    "bytes": "byte",
    "kilobytes": "kibibyte",
    "kb": "kibibyte",
    "megabytes": "mebibyte",
    "mb": "mebibyte",
    "gigabytes": "gibibyte",
    "gb": "gibibyte",
    "terabytes": "tebibyte",
    "tb": "tebibyte",
}

# Temperature conversions handled manually
TEMP_UNITS = {"degc", "degf", "kelvin", "celsius", "fahrenheit", "centigrade"}


def _normalize_unit(unit: str) -> str:
    """Convert natural language unit names to pint-compatible strings."""
    return UNIT_ALIASES.get(unit.lower().strip(), unit.lower().strip())


def _is_temperature(unit: str) -> bool:
    return _normalize_unit(unit).lower() in TEMP_UNITS


def _convert_temperature(value: float, from_unit: str, to_unit: str) -> str:
    """Handle temperature conversions manually."""
    from_norm = from_unit.lower().strip().replace(" ", "")
    to_norm = to_unit.lower().strip().replace(" ", "")

    # Normalize to c/f/k
    def normalize(u):
        if u in ("celsius", "centigrade", "degc", "c"):
            return "c"
        if u in ("fahrenheit", "degf", "f"):
            return "f"
        if u in ("kelvin", "k"):
            return "k"
        return u

    fr = normalize(from_norm)
    to = normalize(to_norm)

    try:
        if fr == "c" and to == "f":
            result = (value * 9/5) + 32
        elif fr == "f" and to == "c":
            result = (value - 32) * 5/9
        elif fr == "c" and to == "k":
            result = value + 273.15
        elif fr == "k" and to == "c":
            result = value - 273.15
        elif fr == "f" and to == "k":
            result = (value - 32) * 5/9 + 273.15
        elif fr == "k" and to == "f":
            result = (value - 273.15) * 9/5 + 32
        elif fr == to:
            result = value
        else:
            return f"I can't convert {from_unit} to {to_unit}."

        result = round(result, 2)
        if result == int(result):
            result = int(result)
        return f"{value} {from_unit} is {result} {to_unit}."
    except Exception:
        return f"I couldn't convert {from_unit} to {to_unit}."


def convert(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert a value from one unit to another.
    Returns a natural language result string.
    """
    if _is_temperature(from_unit) or _is_temperature(to_unit):
        return _convert_temperature(value, from_unit, to_unit)

    from_norm = _normalize_unit(from_unit)
    to_norm = _normalize_unit(to_unit)

    try:
        quantity = ureg.Quantity(value, from_norm)
        result = quantity.to(to_norm)
        result_val = round(result.magnitude, 4)

        # Clean up unnecessary decimals
        if result_val == int(result_val):
            result_val = int(result_val)
        elif result_val > 100:
            result_val = round(result_val, 2)

        return f"{value} {from_unit} is {result_val} {to_unit}."
    except pint.DimensionalityError:
        return f"I can't convert {from_unit} to {to_unit} — they measure different things."
    except pint.UndefinedUnitError:
        return f"I don't recognize the unit '{from_unit}' or '{to_unit}'."
    except Exception:
        return f"I couldn't convert {from_unit} to {to_unit}."