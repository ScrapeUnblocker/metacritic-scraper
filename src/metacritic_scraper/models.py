"""Typed results: titles, full title details, reviews and result pages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _join(values: list[Any]) -> str:
    return " | ".join(str(v) for v in values if v not in (None, ""))


@dataclass
class Title:
    """A game, movie, TV show (or season) or person from a browse list or search."""

    media: str
    title: str
    slug: str
    url: str
    rank: int | None = None
    page: int | None = None
    title_id: int | None = None
    season: int | None = None
    release_date: str | None = None
    year: int | None = None
    content_rating: str | None = None
    metascore: int | None = None
    critic_review_count: int | None = None
    critic_positive: int | None = None
    critic_mixed: int | None = None
    critic_negative: int | None = None
    critic_sentiment: str | None = None
    user_score: float | None = None
    #: Metascore minus the user score on the same 100-point scale. Positive: critics
    #: liked it more than players or viewers did.
    score_gap: float | None = None
    #: Game platforms, or the streaming services a movie or show is on.
    platforms: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    description: str | None = None
    runtime_minutes: int | None = None
    season_count: int | None = None
    #: ``Must-Play`` / ``Must-See`` / ``Must-Watch`` (search results only).
    must_badge: str | None = None
    image: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_row(self) -> dict[str, Any]:
        row = self.to_dict()
        row["platforms"] = _join(self.platforms)
        row["genres"] = _join(self.genres)
        return row


@dataclass
class BrowsePage:
    """One page (24 titles) of a browse list."""

    url: str
    page: int
    total: int | None
    titles: list[Title]

    @property
    def last_page(self) -> int | None:
        if self.total is None:
            return None
        return max(1, -(-self.total // 24))

    @property
    def has_next(self) -> bool:
        return bool(self.titles) and (self.last_page is None or self.page < self.last_page)


@dataclass
class BrowseResults:
    """Titles collected from one or more browse pages."""

    url: str
    total: int | None
    titles: list[Title]
    pages_fetched: int = 0
    #: ``(filter, value)`` pairs Metacritic did not apply (unknown values are dropped).
    ignored_filters: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class PlatformScore:
    """A game's release on one platform with its own Metascore."""

    name: str
    slug: str | None
    lead: bool = False
    release_date: str | None = None
    metascore: int | None = None
    critic_review_count: int | None = None
    critic_sentiment: str | None = None
    url: str | None = None


@dataclass
class Credit:
    """A cast or crew member."""

    name: str
    job: str | None = None
    roles: list[str] = field(default_factory=list)
    url: str | None = None


@dataclass
class Award:
    event: str
    wins: int | None = None
    nominations: int | None = None


@dataclass
class Offer:
    """Where to buy a game, or where to stream, rent or buy a movie or show."""

    kind: str
    store: str
    platform: str | None = None
    price: float | None = None
    original_price: float | None = None
    discount_percent: float | None = None
    currency: str | None = None
    quality: str | None = None
    url: str | None = None


@dataclass
class Bucket:
    label: str
    count: int | None


@dataclass
class PlayerStats:
    """What Metacritic users report about a game: rating, play time, difficulty, status."""

    ratings: list[Bucket] = field(default_factory=list)
    play_time: list[Bucket] = field(default_factory=list)
    difficulty: list[Bucket] = field(default_factory=list)
    play_status: list[Bucket] = field(default_factory=list)


@dataclass
class Season:
    number: int | None
    slug: str | None
    url: str | None
    year: int | None = None
    premiere_date: str | None = None
    episode_count: int | None = None
    metascore: int | None = None
    critic_review_count: int | None = None
    critic_sentiment: str | None = None


@dataclass
class Episode:
    number: int | None
    title: str
    release_date: str | None = None
    runtime_minutes: int | None = None
    content_rating: str | None = None
    description: str | None = None
    url: str | None = None


@dataclass
class TitleDetails:
    """Everything a Metacritic title page shows about a game, movie, show or season."""

    media: str
    title: str
    slug: str
    url: str
    title_id: int | None = None
    season: int | None = None
    description: str | None = None
    tagline: str | None = None
    release_date: str | None = None
    year: int | None = None
    content_rating: str | None = None
    genres: list[str] = field(default_factory=list)
    metascore: int | None = None
    critic_review_count: int | None = None
    critic_positive: int | None = None
    critic_mixed: int | None = None
    critic_negative: int | None = None
    critic_sentiment: str | None = None
    user_score: float | None = None
    #: How many users rated the title.
    user_rating_count: int | None = None
    #: How many of them also wrote a review.
    user_review_count: int | None = None
    user_positive: int | None = None
    user_mixed: int | None = None
    user_negative: int | None = None
    user_sentiment: str | None = None
    score_gap: float | None = None
    must_badge: str | None = None
    # games
    platform: str | None = None
    platforms: list[PlatformScore] = field(default_factory=list)
    developers: list[str] = field(default_factory=list)
    publishers: list[str] = field(default_factory=list)
    franchises: list[str] = field(default_factory=list)
    player_stats: PlayerStats | None = None
    where_to_buy: list[Offer] = field(default_factory=list)
    # movies and TV
    runtime_minutes: int | None = None
    networks: list[str] = field(default_factory=list)
    production_companies: list[str] = field(default_factory=list)
    cast: list[Credit] = field(default_factory=list)
    crew: list[Credit] = field(default_factory=list)
    awards: list[Award] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    imdb_id: str | None = None
    season_count: int | None = None
    seasons: list[Season] = field(default_factory=list)
    episodes: list[Episode] = field(default_factory=list)
    where_to_watch: list[Offer] = field(default_factory=list)
    image: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_row(self) -> dict[str, Any]:
        """A flat summary for CSV and tables (nested lists are left out or joined)."""
        row = {
            k: v
            for k, v in self.to_dict().items()
            if not isinstance(v, (list, dict)) or k in {"genres", "developers", "publishers"}
        }
        row["genres"] = _join(self.genres)
        row["developers"] = _join(self.developers)
        row["publishers"] = _join(self.publishers)
        row["platforms"] = _join([p.name for p in self.platforms])
        row["networks"] = _join(self.networks)
        row["directors"] = _join([c.name for c in self.crew if (c.job or "").startswith("Direct")])
        row["top_cast"] = _join([c.name for c in self.cast[:5]])
        row.pop("description", None)
        return row


@dataclass
class Review:
    """A critic review (``publication``) or a user review (``author``)."""

    kind: str
    score: float | None
    date: str | None
    quote: str | None
    author: str | None = None
    publication: str | None = None
    publication_slug: str | None = None
    url: str | None = None
    review_id: str | None = None
    platform: str | None = None
    season: str | None = None
    spoiler: bool | None = None
    title: str | None = None
    title_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewsPage:
    url: str
    offset: int
    total: int | None
    reviews: list[Review]


@dataclass
class ReviewResults:
    """Reviews collected across pages."""

    title: str
    kind: str
    total: int | None
    reviews: list[Review]
    requests: int = 0


@dataclass
class SearchResults:
    query: str
    kind: str
    total: int | None
    results: list[Title]
