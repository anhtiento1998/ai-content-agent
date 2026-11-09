"""Vietnamese text helpers: Unicode NFC and reading numbers, dates and units aloud.

LLMs and copy-pasted text sometimes produce decomposed Vietnamese (a base
letter followed by combining accents). It looks identical but breaks font
shaping in libass on Windows, string comparisons and TTS — so every text the
studio uses is normalised to NFC first.

TTS engines read "26°C", "50.000đ" or "5/11/2026" unreliably in Vietnamese,
so narration is converted to words before synthesis ("hai mươi sáu độ C").
Captions keep the original digits, which read faster on screen;
`spoken_words` keeps a one-to-one mapping between the two so caption timing
can be weighted by how long each word takes to say.
"""

from __future__ import annotations

import re
import unicodedata

_DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
_SCALES = ["", "nghìn", "triệu", "tỷ"]

_UNITS = {
    "km": "ki-lô-mét", "m": "mét", "cm": "xen-ti-mét", "mm": "mi-li-mét",
    "kg": "ki-lô-gam", "g": "gam", "mg": "mi-li-gam", "l": "lít", "ml": "mi-li-lít",
    "kwh": "ki-lô-oát giờ", "w": "oát", "kw": "ki-lô-oát", "v": "vôn",
    "gb": "gi-ga-bai", "mb": "mê-ga-bai", "tb": "tê-ra-bai",
    "km/h": "ki-lô-mét trên giờ", "m2": "mét vuông", "m²": "mét vuông", "m3": "mét khối", "m³": "mét khối",
    "ha": "héc-ta", "s": "giây", "p": "phút", "h": "giờ",
    "°c": "độ C", "độc": "độ C", "°f": "độ F", "°": "độ", "%": "phần trăm",
    "đ": "đồng", "₫": "đồng", "vnd": "đồng", "vnđ": "đồng", "k": "nghìn",
    "usd": "đô la", "$": "đô la", "tr": "triệu",
}
_PREFIX_CURRENCY = {"$": "đô la"}

_NUMBER = r"\d+(?:[.,]\d+)*"
_WORD_RE = re.compile(rf"^(?P<pre>[(\"'“‘\[]*)(?P<cur>\$)?(?P<num>{_NUMBER})(?P<unit>[^\W\d_]*[²³/]?[^\W\d_]*|%|°[cCfF]?|₫)?(?P<post>[.,!?;:…)\"'”’\]]*)$")
_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})(?:/(\d{4}))?$")
_TIME_RE = re.compile(r"^(\d{1,2})(?:h|:)(\d{2})?(?:p|')?$", re.IGNORECASE)
_RANGE_RE = re.compile(rf"^({_NUMBER})[-–]({_NUMBER})(.*)$")
_TRAIL = ".,!?;:…)\"'”’]"


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def _below_thousand(n: int, *, full: bool) -> str:
    """0-999; `full` reads leading zeros (không trăm lẻ ...) for groups after the first."""

    hundreds, rest = divmod(n, 100)
    tens, ones = divmod(rest, 10)
    words: list[str] = []
    if hundreds or full:
        words += [_DIGITS[hundreds], "trăm"]
    if tens == 0:
        if ones:
            if hundreds or full:
                words.append("lẻ")
            words.append(_DIGITS[ones])
    elif tens == 1:
        words.append("mười")
        if ones:
            words.append("lăm" if ones == 5 else _DIGITS[ones])
    else:
        words += [_DIGITS[tens], "mươi"]
        if ones == 1:
            words.append("mốt")
        elif ones == 4:
            words.append("tư")
        elif ones == 5:
            words.append("lăm")
        elif ones:
            words.append(_DIGITS[ones])
    return " ".join(words)


def read_integer(n: int) -> str:
    """Vietnamese words for a whole number: 2026 -> hai nghìn không trăm hai mươi sáu."""

    if n < 0:
        return "âm " + read_integer(-n)
    if n < 10:
        return _DIGITS[n]
    if n >= 10**12:
        return " ".join(_DIGITS[int(d)] for d in str(n))  # phone numbers, IDs: digit by digit
    groups: list[int] = []
    while n:
        n, group = divmod(n, 1000)
        groups.append(group)
    words: list[str] = []
    for index in range(len(groups) - 1, -1, -1):
        group = groups[index]
        if group == 0:
            continue
        is_first = index == len(groups) - 1
        words.append(_below_thousand(group, full=not is_first))
        if _SCALES[index]:
            words.append(_SCALES[index])
    return " ".join(words)


def read_number(token: str) -> str:
    """'1.000.000' -> một triệu; '3,5' / '3.5' -> ba phẩy năm; '007' -> không không bảy."""

    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", token) or re.fullmatch(r"\d{1,3}(?:,\d{3}){2,}", token):
        return read_integer(int(re.sub(r"[.,]", "", token)))
    match = re.fullmatch(r"(\d+)[.,](\d+)", token)
    if match:
        whole, fraction = match.groups()
        fraction_words = read_integer(int(fraction)) if len(fraction) <= 2 and not fraction.startswith("0") \
            else " ".join(_DIGITS[int(d)] for d in fraction)
        return f"{read_integer(int(whole))} phẩy {fraction_words}"
    digits = re.sub(r"[.,]", "", token)
    if len(digits) > 1 and digits.startswith("0"):
        return " ".join(_DIGITS[int(d)] for d in digits)
    return read_integer(int(digits))


def _split_trailing(word: str) -> tuple[str, str]:
    core = word.rstrip(_TRAIL)
    return core, word[len(core):]


def _spoken_word(word: str, previous: str | None, following: str | None) -> str:
    core, trail = _split_trailing(word)
    lead = core[: len(core) - len(core.lstrip("(\"'“‘["))]
    core = core[len(lead):]
    if not core or not any(ch.isdigit() for ch in core):
        unit = _UNITS.get(core.lower()) if previous and re.search(r"\d$", previous.rstrip(_TRAIL)) else None
        return f"{lead}{unit}{trail}" if unit else word

    date = _DATE_RE.match(core)
    if date and int(date.group(1)) <= 31 and 1 <= int(date.group(2)) <= 12 and (
        date.group(3) or (previous or "").lower() == "ngày"
    ):
        day, month, year = date.groups()
        words = ("" if (previous or "").lower() == "ngày" else "ngày ") + f"{read_integer(int(day))} tháng {read_integer(int(month))}"
        if year:
            words += f" năm {read_integer(int(year))}"
        return f"{lead}{words}{trail}"

    clock = _TIME_RE.match(core)
    if clock and int(clock.group(1)) <= 24 and (clock.group(2) is None or int(clock.group(2)) < 60):
        words = f"{read_integer(int(clock.group(1)))} giờ"
        if clock.group(2) and int(clock.group(2)):
            words += f" {read_integer(int(clock.group(2)))}"
        return f"{lead}{words}{trail}"

    span = _RANGE_RE.match(core)
    if span:
        left = read_number(span.group(1))
        right = _spoken_word(span.group(2) + span.group(3), None, following)
        return f"{lead}{left} đến {right}{trail}"

    match = _WORD_RE.match(core)
    if not match:
        return word
    number = read_number(match.group("num"))
    unit_text = (match.group("unit") or "").lower()
    if (previous or "").lower() == "thứ" and match.group("num") in ("1", "4") and not unit_text:
        number = "nhất" if match.group("num") == "1" else "tư"
    parts = [number]
    if unit_text:
        parts.append(_UNITS.get(unit_text, match.group("unit")))
        if unit_text == "k" and (following or "").lower().rstrip(_TRAIL) not in ("đồng", "đ", "vnd", "vnđ"):
            parts.append("đồng")
    if match.group("cur"):
        parts.append(_PREFIX_CURRENCY[match.group("cur")])
    return f"{lead}{match.group('pre') or ''}{' '.join(parts)}{match.group('post') or ''}{trail}"


def spoken_words(words: list[str], language: str = "vi") -> list[str]:
    """The spoken form of each word, one-to-one with `words` (a word may become several)."""

    words = [nfc(w) for w in words]
    if language != "vi":
        return words
    return [
        _spoken_word(word, words[i - 1] if i else None, words[i + 1] if i + 1 < len(words) else None)
        for i, word in enumerate(words)
    ]


def spoken(text: str, language: str = "vi") -> str:
    """Narration as the TTS engine should read it."""

    return " ".join(spoken_words(nfc(text).split(), language))


def syllables(text: str) -> int:
    """Vietnamese is one syllable per space-separated word; a cheap proxy for speaking time."""

    return max(1, len(re.findall(r"[^\W_]+", text)))
