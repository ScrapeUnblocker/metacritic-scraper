"""Scrape Metacritic games, movies and TV shows through the ScrapeUnblocker API.

>>> from metacritic_scraper import BrowseFilters, Metacritic
>>> mc = Metacritic()  # reads SCRAPEUNBLOCKER_KEY
>>> best = mc.browse("game", BrowseFilters(platforms=["ps5"], year=2025), pages=2)
>>> [(t.title, t.metascore, t.user_score) for t in best.titles[:5]]
>>> game = mc.title("elden-ring")
>>> game.metascore, game.user_score, [(p.name, p.metascore) for p in game.platforms]
>>> reviews = mc.reviews("movie/oppenheimer", kind="user", sentiment="negative", limit=50)

See https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos
"""

from __future__ import annotations

__version__ = "0.1.0"

from .errors import FilterError, MetacriticError, NotFoundError, ParseError
from .models import (
    Award,
    BrowsePage,
    BrowseResults,
    Bucket,
    Credit,
    Episode,
    Offer,
    PlatformScore,
    PlayerStats,
    Review,
    ReviewResults,
    ReviewsPage,
    SearchResults,
    Season,
    Title,
    TitleDetails,
)
from .options import (
    GAME_GENRES,
    MEDIA,
    NETWORKS,
    PLATFORMS,
    REVIEW_SORTS,
    SCREEN_GENRES,
    SEARCH_TYPES,
    SENTIMENTS,
    SORTS,
    BrowseFilters,
)
from .parsing import parse_browse, parse_reviews, parse_search, parse_title, score_gap
from .scraper import Metacritic, ignored_filters
from .urls import TitleRef, parse_ref

__all__ = [
    "Award",
    "BrowseFilters",
    "BrowsePage",
    "BrowseResults",
    "Bucket",
    "Credit",
    "Episode",
    "FilterError",
    "GAME_GENRES",
    "MEDIA",
    "Metacritic",
    "MetacriticError",
    "NETWORKS",
    "NotFoundError",
    "Offer",
    "PLATFORMS",
    "ParseError",
    "PlatformScore",
    "PlayerStats",
    "REVIEW_SORTS",
    "Review",
    "ReviewResults",
    "ReviewsPage",
    "SCREEN_GENRES",
    "SEARCH_TYPES",
    "SENTIMENTS",
    "SORTS",
    "SearchResults",
    "Season",
    "Title",
    "TitleDetails",
    "TitleRef",
    "__version__",
    "ignored_filters",
    "parse_browse",
    "parse_ref",
    "parse_reviews",
    "parse_search",
    "parse_title",
    "score_gap",
]
