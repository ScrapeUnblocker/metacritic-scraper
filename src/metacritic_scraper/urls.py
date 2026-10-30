"""Metacritic URLs: browse lists, title pages, review feeds, search and images."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

from .options import SEARCH_TYPES, media_name

BASE_URL = "https://www.metacritic.com"
#: The JSON service Metacritic's own pages load reviews and search results from.
API_URL = "https://backend.metacritic.com"
IMAGE_URL = "https://www.metacritic.com/a/img/catalog"

_API_TYPES = {"game": "games", "movie": "movies", "tv": "shows"}
_SEASON_RE = re.compile(r"^(season-\d+|specials)$")
# Path parts after the title slug that name a sub-page rather than a season.
_SUB_PAGES = {"critic-reviews", "user-reviews", "details", "trivia", "news", "credits"}


@dataclass(frozen=True)
class TitleRef:
    """A game, movie or TV show (optionally one season of it) on Metacritic."""

    media: str
    slug: str
    season: str | None = None

    @property
    def url(self) -> str:
        url = f"{BASE_URL}/{self.media}/{self.slug}/"
        return f"{url}{self.season}/" if self.season else url


def season_slug(value: str | int | None) -> str | None:
    """``3``, ``"3"``, ``"Season 3"`` or ``"season-3"`` -> ``"season-3"``."""
    if value is None or value == "":
        return None
    text = str(value).strip().lower().replace(" ", "-")
    if text in {"0", "specials", "special"}:
        return "specials"
    if text.isdigit():
        return f"season-{int(text)}"
    if _SEASON_RE.match(text):
        return text
    raise ValueError(f"not a season: {value!r} (use a number such as 3, or 'specials')")


def parse_ref(ref: str, media: str | None = None, season: str | int | None = None) -> TitleRef:
    """Read a title from a slug, ``media/slug`` or a metacritic.com URL.

    >>> parse_ref("elden-ring")
    TitleRef(media='game', slug='elden-ring', season=None)
    >>> parse_ref("https://www.metacritic.com/tv/the-bear/season-3/")
    TitleRef(media='tv', slug='the-bear', season='season-3')

    Args:
        ref: ``elden-ring``, ``movie/oppenheimer``, ``tv/the-bear/season-3`` or a URL.
        media: Media type for a bare slug (default ``game``); ignored when ``ref`` names one.
        season: A TV season (``3`` or ``season-3``); overrides one in ``ref``.
    """
    text = str(ref or "").strip()
    if not text:
        raise ValueError("a Metacritic title slug or URL, e.g. elden-ring")
    if "://" in text or text.startswith("www."):
        parts = urlsplit(text if "://" in text else "https://" + text)
        if not parts.netloc.lower().endswith("metacritic.com"):
            raise ValueError(f"not a Metacritic URL: {ref}")
        text = parts.path
    parts_list = [p for p in text.strip("/").split("/") if p]
    found_media: str | None = None
    if len(parts_list) >= 2:
        try:
            found_media = media_name(parts_list[0])
            parts_list = parts_list[1:]
        except ValueError:
            found_media = None
    if not parts_list:
        raise ValueError(f"no title slug in {ref!r}")
    slug = parts_list[0].lower()
    found_season = None
    if len(parts_list) > 1 and parts_list[1] not in _SUB_PAGES:
        try:
            found_season = season_slug(parts_list[1])
        except ValueError:
            found_season = None
    kind = found_media or (media_name(media) if media else "game")
    chosen = season_slug(season) if season not in (None, "") else found_season
    if chosen and kind != "tv":
        raise ValueError("seasons exist only for TV shows")
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        raise ValueError(f"not a Metacritic slug: {slug!r}")
    return TitleRef(kind, slug, chosen)


def _query(params: list[tuple[str, str]]) -> str:
    return "&".join(f"{quote(str(k), safe='')}={quote(str(v), safe='')}" for k, v in params)


def browse_url(
    media: str, time: str, sort: str, params: list[tuple[str, str]], page: int = 1
) -> str:
    """A ``/browse/<media>/all/all/<time>/<sort>/`` list URL (page 1 has no page param)."""
    media = media_name(media)
    query = list(params) + ([("page", str(page))] if page > 1 else [])
    url = f"{BASE_URL}/browse/{media}/all/all/{time}/{sort}/"
    return f"{url}?{_query(query)}" if query else url


def reviews_url(
    ref: TitleRef,
    kind: str,
    *,
    platform: str | None = None,
    sentiment: str = "all",
    sort: str | None = None,
    offset: int = 0,
    limit: int = 10,
) -> str:
    """The JSON feed behind a title's critic or user review page."""
    if ref.media == "tv" and ref.season:
        path = f"seasons/{ref.slug}/season/{ref.season}"
    else:
        path = f"{_API_TYPES[ref.media]}/{ref.slug}"
        if platform and ref.media == "game":
            path += f"/platform/{platform}"
    params = [
        ("offset", str(offset)),
        ("limit", str(limit)),
        ("filterBySentiment", sentiment),
        ("sort", sort or ("score" if kind == "critic" else "date")),
    ]
    return f"{API_URL}/reviews/metacritic/{kind}/{path}/web?{_query(params)}"


def search_url(query: str, kind: str = "all", offset: int = 0, limit: int = 30) -> str:
    """The JSON feed behind Metacritic's search page."""
    params = [("offset", str(offset)), ("limit", str(limit)), ("mcoTypeId", SEARCH_TYPES[kind])]
    return f"{API_URL}/finder/metacritic/search/{quote(query.strip(), safe='')}/web?" + _query(
        params
    )


def image_url(path: str | None) -> str | None:
    """A full image URL from Metacritic's catalog path (``/provider/6/3/....jpg``)."""
    if not path:
        return None
    if path.startswith("http"):
        return path
    return IMAGE_URL + ("" if path.startswith("/") else "/") + path


def absolute(url: str | None) -> str | None:
    if not url:
        return None
    return url if url.startswith("http") else BASE_URL + ("" if url.startswith("/") else "/") + url
