import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit


def normalize_name(name: str | None) -> str | None:
    """
    Normalize entity names for matching.
    """

    if not name:
        return None

    name = unicodedata.normalize("NFKC", name)

    name = re.sub(r"\s+", " ", name).strip()

    return name.casefold() or None


def normalize_website(url: str | None) -> str | None:
    """
    Normalize website URLs for matching.
    """

    if not url:
        return None

    url = url.strip()

    if not url:
        return None

    if "://" not in url:
        url = "https://" + url

    try:
        parsed = urlsplit(url)

        hostname = parsed.hostname

        if not hostname:
            return None

        hostname = hostname.lower().rstrip(".")

        if hostname.startswith("www."):
            hostname = hostname[4:]

        port = parsed.port

        if port in (80, 443):
            port = None

        netloc = hostname

        if port is not None:
            netloc = f"{hostname}:{port}"

        path = parsed.path.rstrip("/")

        return urlunsplit(
            (
                "https",
                netloc,
                path,
                "",
                "",
            )
        )

    except ValueError:
        return None


def normalize_category(category: str | None) -> str | None:
    """
    Normalize categories for consistent storage.
    """

    if not category:
        return None

    category = re.sub(
        r"\s+",
        " ",
        category,
    ).strip()

    return category.casefold() or None