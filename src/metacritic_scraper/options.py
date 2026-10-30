"""The filter values Metacritic's browse pages, reviews and search accept.

Metacritic silently ignores a browse filter value it does not know and returns the
unfiltered list instead, so every value is checked here before a request is spent.
The tables below were read from Metacritic's own filter menus.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .errors import FilterError

MEDIA = ("game", "movie", "tv")
_MEDIA_ALIASES = {
    "game": "game",
    "games": "game",
    "movie": "movie",
    "movies": "movie",
    "film": "movie",
    "films": "movie",
    "tv": "tv",
    "show": "tv",
    "shows": "tv",
    "tv-show": "tv",
    "tv-shows": "tv",
    "series": "tv",
}

#: Browse sort orders: our name -> the URL segment Metacritic uses.
SORTS = {"metascore": "metascore", "userscore": "userscore", "newest": "new"}
_SORT_ALIASES = {"user-score": "userscore", "user": "userscore", "new": "newest", "date": "newest"}

#: Review sort orders: our name -> Metacritic's value. ``publication`` is critics only.
REVIEW_SORTS = {"score": "score", "newest": "date", "publication": "publication"}

#: Review sentiment filters: our name -> Metacritic's value.
SENTIMENTS = {"all": "all", "positive": "positive", "mixed": "neutral", "negative": "negative"}

REVIEW_KINDS = ("critic", "user")

#: Search tabs: our name -> Metacritic's content type ids.
SEARCH_TYPES = {"all": "1,2,3,13", "game": "13", "movie": "2", "tv": "1", "person": "3"}


@dataclass(frozen=True)
class Choice:
    """One value of a browse filter."""

    #: The value Metacritic's browse URL takes (``ps5``, ``netflix``).
    slug: str
    #: The name in Metacritic's filter menu (``PS5``, ``Netflix``).
    label: str
    #: The name Metacritic prints on matching titles (``PlayStation 5``).
    shown_as: str
    aliases: tuple[str, ...] = ()


PLATFORMS: dict[str, Choice] = {
    c.slug: c
    for c in (
        Choice("ps5", "PS5", "PlayStation 5", ("playstation-5",)),
        Choice("xbox-series-x", "Xbox Series X/S", "Xbox Series X", ("xbox-series", "xsx")),
        Choice("nintendo-switch-2", "Nintendo Switch 2", "Nintendo Switch 2", ("switch-2",)),
        Choice("nintendo-switch", "Nintendo Switch", "Nintendo Switch", ("switch",)),
        Choice("pc", "PC", "PC", ("windows",)),
        Choice("mobile", "Mobile", "iOS (iPhone/iPad)", ("ios", "iphone")),
        Choice("3ds", "3DS", "3DS", ("nintendo-3ds",)),
        Choice("dreamcast", "Dreamcast", "Dreamcast"),
        Choice("nintendo-ds", "Nintendo DS", "DS", ("ds",)),
        Choice("game-boy-advance", "Game Boy Advance", "Game Boy Advance", ("gba",)),
        Choice("gamecube", "GameCube", "GameCube"),
        Choice("meta-quest", "Meta Quest", "Meta Quest", ("quest", "oculus-quest")),
        Choice("nintendo-64", "Nintendo 64", "Nintendo 64", ("n64",)),
        Choice("ps1", "PS1", "PlayStation", ("playstation", "psx")),
        Choice("ps2", "PS2", "PlayStation 2", ("playstation-2",)),
        Choice("ps3", "PS3", "PlayStation 3", ("playstation-3",)),
        Choice("ps4", "PS4", "PlayStation 4", ("playstation-4",)),
        Choice("psp", "PSP", "PSP"),
        Choice("ps-vita", "PS Vita", "PlayStation Vita", ("vita", "playstation-vita")),
        Choice("wii", "Wii", "Wii"),
        Choice("wii-u", "Wii U", "Wii U"),
        Choice("xbox", "Xbox", "Xbox"),
        Choice("xbox-360", "Xbox 360", "Xbox 360"),
        Choice("xbox-one", "Xbox One", "Xbox One"),
    )
}

NETWORKS: dict[str, Choice] = {
    c.slug: c
    for c in (
        Choice("netflix", "Netflix", "Netflix"),
        Choice("prime-video", "Prime Video", "Prime Video", ("amazon-prime", "prime")),
        Choice("disney-plus", "Disney+", "Disney+"),
        Choice("hbo-max", "HBO Max", "Max", ("max", "hbo")),
        Choice("hulu", "Hulu", "Hulu"),
        Choice("apple-tv", "Apple TV", "Apple TV+", ("apple-tv-plus",)),
        Choice("paramount-plus", "Paramount+", "Paramount+"),
        Choice("peacock", "Peacock", "Peacock"),
        Choice("amazon", "Amazon (Buy/Rent)", "Amazon", ("amazon-buy-rent",)),
        Choice("itunes", "iTunes", "iTunes"),
        Choice("vudu", "Vudu", "Vudu", ("fandango-at-home",)),
        Choice("youtube-premium", "YouTube Premium", "YouTube Premium"),
        Choice("criterion-channel", "Criterion Channel", "Criterion Channel", ("criterion",)),
        Choice("discovery-plus", "Discovery+", "Discovery+"),
        Choice("fubotv", "fuboTV", "fuboTV", ("fubo",)),
        Choice("plex", "Plex", "Plex"),
        Choice("pluto", "Pluto", "Pluto", ("pluto-tv",)),
        Choice("starz", "Starz", "Starz"),
        Choice("sundance-now", "Sundance Now", "Sundance Now"),
        Choice("tubi", "Tubi", "Tubi"),
    )
}

GAME_GENRES = (
    "Action",
    "Action Adventure",
    "Action Puzzle",
    "Action RPG",
    "Adventure",
    "Application",
    "Arcade",
    "Beat-'Em-Up",
    "Board / Card Game",
    "Card Battle",
    "Compilation",
    "Edutainment",
    "Exercise / Fitness",
    "Fighting",
    "First-Person Shooter",
    "Gambling",
    "General",
    "MMORPG",
    "Open-World",
    "Party / Minigame",
    "Pinball",
    "Platformer",
    "Puzzle",
    "RPG",
    "Racing",
    "Real-Time Strategy",
    "Rhythm",
    "Roguelike",
    "Sandbox",
    "Shooter",
    "Simulation",
    "Sports",
    "Strategy",
    "Survival",
    "Tactics",
    "Third-Person Shooter",
    "Trivia / Game Show",
    "Turn-Based Strategy",
    "Virtual",
    "Visual Novel",
)

#: Genres for movies and TV shows.
SCREEN_GENRES = (
    "Action",
    "Adventure",
    "Animation",
    "Biography",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Family",
    "Fantasy",
    "Film-Noir",
    "Game-Show",
    "History",
    "Horror",
    "Music",
    "Musical",
    "Mystery",
    "News",
    "Reality-TV",
    "Romance",
    "Sci-Fi",
    "Short",
    "Sport",
    "Talk-Show",
    "Thriller",
    "War",
    "Western",
)

_GENRE_ALIASES = {
    "fps": "First-Person Shooter",
    "tps": "Third-Person Shooter",
    "rts": "Real-Time Strategy",
    "science-fiction": "Sci-Fi",
    "scifi": "Sci-Fi",
    "noir": "Film-Noir",
    "sports": "Sport",
}


def _norm(text: str) -> str:
    """A loose key for matching user input: ``Disney+`` == ``disney-plus``."""
    text = str(text).lower().replace("+", "plus").replace("&", "and")
    return re.sub(r"[^a-z0-9]", "", text)


def media_name(value: str) -> str:
    """``game``, ``movie`` or ``tv`` for any common spelling (``games``, ``shows``, ...)."""
    key = str(value or "").strip().lower().replace(" ", "-").replace("_", "-")
    if key not in _MEDIA_ALIASES:
        raise FilterError(f"unknown media type {value!r}; use one of: {', '.join(MEDIA)}")
    return _MEDIA_ALIASES[key]


def sort_name(value: str | None) -> str | None:
    """The canonical browse sort name, or ``None`` for Metacritic's default (metascore)."""
    if value is None or value == "":
        return None
    key = str(value).strip().lower().replace("_", "-").replace(" ", "-")
    key = _SORT_ALIASES.get(key, key)
    if key not in SORTS:
        raise FilterError(f"unknown sort {value!r}; use one of: {', '.join(SORTS)}")
    return key


def _resolve(value: str, table: dict[str, Choice], what: str) -> Choice:
    key = _norm(value)
    for choice in table.values():
        names = (choice.slug, choice.label, choice.shown_as, *choice.aliases)
        if key in {_norm(name) for name in names}:
            return choice
    raise FilterError(f"unknown {what} {value!r}; use one of: {', '.join(table)}")


def resolve_platform(value: str) -> Choice:
    """A game platform by slug, menu label or display name (``ps5``, ``PS5``, ``PlayStation 5``)."""
    return _resolve(value, PLATFORMS, "platform")


def resolve_network(value: str) -> Choice:
    """A streaming service by slug or name (``netflix``, ``Disney+``, ``max``)."""
    return _resolve(value, NETWORKS, "streaming service")


def genres_for(media: str) -> tuple[str, ...]:
    return GAME_GENRES if media_name(media) == "game" else SCREEN_GENRES


def resolve_genre(value: str, media: str) -> str:
    """The genre label Metacritic expects (``action-rpg`` -> ``Action RPG``)."""
    genres = genres_for(media)
    key = _norm(value)
    alias = _GENRE_ALIASES.get(str(value).strip().lower().replace(" ", "-"))
    for genre in genres:
        if key == _norm(genre) or alias == genre:
            return genre
    raise FilterError(
        f"unknown {media_name(media)} genre {value!r}; use one of: {', '.join(genres)}"
    )


def review_sort(value: str | None, kind: str) -> str | None:
    if value is None or value == "":
        return None
    key = str(value).strip().lower()
    key = {"date": "newest", "new": "newest", "rating": "score"}.get(key, key)
    if key not in REVIEW_SORTS or (key == "publication" and kind != "critic"):
        valid = [s for s in REVIEW_SORTS if kind == "critic" or s != "publication"]
        raise FilterError(f"unknown {kind} review sort {value!r}; use one of: {', '.join(valid)}")
    return REVIEW_SORTS[key]


def sentiment_value(value: str | None) -> str:
    key = str(value or "all").strip().lower()
    key = {"neutral": "mixed", "positive-reviews": "positive", "negative-reviews": "negative"}.get(
        key, key
    )
    if key not in SENTIMENTS:
        raise FilterError(f"unknown sentiment {value!r}; use one of: {', '.join(SENTIMENTS)}")
    return SENTIMENTS[key]


def review_kind(value: str | None) -> str:
    key = str(value or "critic").strip().lower().rstrip("s")
    if key not in REVIEW_KINDS:
        raise FilterError(f"unknown review kind {value!r}; use one of: {', '.join(REVIEW_KINDS)}")
    return key


def search_type(value: str | None) -> str:
    key = str(value or "all").strip().lower()
    key = {"people": "person", "persons": "person"}.get(key, key)
    if key != "all" and key != "person":
        key = media_name(key)
    if key not in SEARCH_TYPES:
        raise FilterError(f"unknown search type {value!r}; use one of: {', '.join(SEARCH_TYPES)}")
    return key


def review_platform(value: str | None) -> str | None:
    """The platform slug used in review URLs (``ps5`` -> ``playstation-5``).

    Title pages name platforms by their display name (``PlayStation 5``), slugged.
    Unknown values pass through unchanged: a title's exact slugs are listed in
    ``TitleDetails.platforms``.
    """
    if not value:
        return None
    slug = str(value).strip().lower().replace(" ", "-")
    try:
        shown_as = resolve_platform(slug).shown_as
    except FilterError:
        return slug
    words = re.sub(r"[^a-z0-9 -]", "", shown_as.lower()).split()
    return "-".join(words)


@dataclass
class BrowseFilters:
    """Filters for Metacritic's browse lists (``/browse/game/``, ``/browse/movie/``, ...).

    Args:
        platforms: Game platforms (``ps5``, ``pc``, ``nintendo-switch``, ...). Games only.
        networks: Streaming services (``netflix``, ``prime-video``, ...). Movies and TV only.
        genres: Genres by name or slug (``Action RPG`` / ``action-rpg``, ``Drama``).
        year: Released in this year.
        year_from: Released in or after this year.
        year_to: Released in or before this year.
        sort: ``metascore`` (default), ``userscore`` or ``newest``.
        extra: Any other ``(name, value)`` query parameters, passed through unchecked.
    """

    platforms: list[str] = field(default_factory=list)
    networks: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    year: int | None = None
    year_from: int | None = None
    year_to: int | None = None
    sort: str | None = None
    extra: list[tuple[str, str]] = field(default_factory=list)

    def checked_choices(self, media: str) -> tuple[str, list[Choice]]:
        """The ``(filter name, choices)`` Metacritic should echo on every title, if any."""
        media = media_name(media)
        if media == "game":
            return "platform", [resolve_platform(p) for p in self.platforms]
        return "network", [resolve_network(n) for n in self.networks]

    def to_url_parts(self, media: str) -> tuple[str, str, list[tuple[str, str]]]:
        """``(time segment, sort segment, query params)`` for a browse URL.

        Raises:
            FilterError: a value Metacritic does not know, or filters that do not fit
                together (platforms on movies, a year plus a year range, ...).
        """
        media = media_name(media)
        if media == "game" and self.networks:
            raise FilterError("streaming services filter movies and TV shows, not games")
        if media != "game" and self.platforms:
            raise FilterError("platforms filter games; use networks for movies and TV shows")
        if self.year is not None and (self.year_from is not None or self.year_to is not None):
            raise FilterError("use either a year or a year range, not both")
        for name, value in (("year", self.year), ("year_from", self.year_from)):
            if value is not None and not 1900 <= int(value) <= 2100:
                raise FilterError(f"{name} {value} is not a plausible release year")
        if self.year_to is not None and not 1900 <= int(self.year_to) <= 2100:
            raise FilterError(f"year_to {self.year_to} is not a plausible release year")
        if (
            self.year_from is not None
            and self.year_to is not None
            and int(self.year_from) > int(self.year_to)
        ):
            raise FilterError(f"year_from {self.year_from} is after year_to {self.year_to}")

        time = str(int(self.year)) if self.year is not None else "all-time"
        sort = SORTS[sort_name(self.sort) or "metascore"]
        params: list[tuple[str, str]] = []
        if self.year_from is not None or self.year_to is not None:
            params.append(("releaseYearMin", str(int(self.year_from or 1900))))
            params.append(("releaseYearMax", str(int(self.year_to or 2100))))
        for platform in self.platforms:
            params.append(("platform", resolve_platform(platform).slug))
        for network in self.networks:
            params.append(("network", resolve_network(network).slug))
        for genre in self.genres:
            params.append(("genre", resolve_genre(genre, media)))
        params.extend((str(k), str(v)) for k, v in self.extra)
        return time, sort, params
