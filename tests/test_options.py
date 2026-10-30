from __future__ import annotations

import pytest

from metacritic_scraper import BrowseFilters, FilterError
from metacritic_scraper.options import (
    media_name,
    resolve_genre,
    resolve_network,
    resolve_platform,
    review_kind,
    review_platform,
    review_sort,
    search_type,
    sentiment_value,
    sort_name,
)


@pytest.mark.parametrize(
    ("value", "slug"),
    [
        ("ps5", "ps5"),
        ("PS5", "ps5"),
        ("PlayStation 5", "ps5"),
        ("Xbox Series X/S", "xbox-series-x"),
        ("switch", "nintendo-switch"),
        ("Nintendo Switch 2", "nintendo-switch-2"),
        ("ds", "nintendo-ds"),
        ("PS Vita", "ps-vita"),
    ],
)
def test_resolve_platform(value, slug):
    assert resolve_platform(value).slug == slug


@pytest.mark.parametrize(
    ("value", "slug"),
    [
        ("Disney+", "disney-plus"),
        ("max", "hbo-max"),
        ("HBO Max", "hbo-max"),
        ("Netflix", "netflix"),
    ],
)
def test_resolve_network(value, slug):
    assert resolve_network(value).slug == slug


def test_unknown_values_list_the_valid_ones():
    with pytest.raises(FilterError, match="ps5, xbox-series-x"):
        resolve_platform("ps6")
    with pytest.raises(FilterError, match="netflix"):
        resolve_network("blockbuster")


@pytest.mark.parametrize(
    ("value", "media", "label"),
    [
        ("action-rpg", "game", "Action RPG"),
        ("Action RPG", "game", "Action RPG"),
        ("fps", "game", "First-Person Shooter"),
        ("party-minigame", "game", "Party / Minigame"),
        ("drama", "movie", "Drama"),
        ("sci-fi", "tv", "Sci-Fi"),
        ("science fiction", "movie", "Sci-Fi"),
    ],
)
def test_resolve_genre(value, media, label):
    assert resolve_genre(value, media) == label


def test_genres_depend_on_media():
    with pytest.raises(FilterError):
        resolve_genre("Roguelike", "movie")


def test_browse_filters_to_url_parts():
    filters = BrowseFilters(
        platforms=["PS5", "pc"],
        genres=["action-rpg"],
        year_from=2020,
        year_to=2025,
        sort="user-score",
        extra=[("foo", "bar")],
    )
    assert filters.to_url_parts("game") == (
        "all-time",
        "userscore",
        [
            ("releaseYearMin", "2020"),
            ("releaseYearMax", "2025"),
            ("platform", "ps5"),
            ("platform", "pc"),
            ("genre", "Action RPG"),
            ("foo", "bar"),
        ],
    )
    assert BrowseFilters(year=2024, sort="newest").to_url_parts("movie") == ("2024", "new", [])
    assert BrowseFilters(networks=["netflix"]).to_url_parts("tv")[2] == [("network", "netflix")]


@pytest.mark.parametrize(
    ("filters", "media"),
    [
        (BrowseFilters(platforms=["ps5"]), "movie"),
        (BrowseFilters(networks=["netflix"]), "game"),
        (BrowseFilters(year=2024, year_from=2020), "game"),
        (BrowseFilters(year_from=2025, year_to=2020), "game"),
        (BrowseFilters(year=1066), "movie"),
        (BrowseFilters(sort="popular"), "game"),
        (BrowseFilters(genres=["Roguelike"]), "tv"),
    ],
)
def test_browse_filters_reject(filters, media):
    with pytest.raises(FilterError):
        filters.to_url_parts(media)


def test_checked_choices():
    name, choices = BrowseFilters(platforms=["ps5"]).checked_choices("game")
    assert name == "platform"
    assert [c.shown_as for c in choices] == ["PlayStation 5"]
    name, choices = BrowseFilters(networks=["max"]).checked_choices("movie")
    assert (name, [c.shown_as for c in choices]) == ("network", ["Max"])


def test_small_vocabularies():
    assert media_name("Shows") == "tv"
    assert media_name("films") == "movie"
    with pytest.raises(FilterError):
        media_name("music")
    assert sort_name(None) is None
    assert sort_name("date") == "newest"
    assert sentiment_value("mixed") == "neutral"
    assert sentiment_value(None) == "all"
    assert review_kind("users") == "user"
    assert search_type("games") == "game"
    assert search_type("people") == "person"


def test_review_sort():
    assert review_sort("newest", "critic") == "date"
    assert review_sort("publication", "critic") == "publication"
    assert review_sort(None, "user") is None
    with pytest.raises(FilterError):
        review_sort("publication", "user")


@pytest.mark.parametrize(
    ("value", "slug"),
    [
        ("ps5", "playstation-5"),
        ("PlayStation 4", "playstation-4"),
        ("pc", "pc"),
        ("xbox-series-x", "xbox-series-x"),
        ("ios-iphoneipad", "ios-iphoneipad"),
        (None, None),
    ],
)
def test_review_platform(value, slug):
    assert review_platform(value) == slug
