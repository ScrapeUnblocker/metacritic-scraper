from __future__ import annotations

import pytest

from metacritic_scraper.urls import (
    TitleRef,
    browse_url,
    image_url,
    parse_ref,
    reviews_url,
    search_url,
    season_slug,
)


@pytest.mark.parametrize(
    ("ref", "media", "season", "expected"),
    [
        ("elden-ring", None, None, TitleRef("game", "elden-ring")),
        ("oppenheimer", "movie", None, TitleRef("movie", "oppenheimer")),
        ("movie/oppenheimer", "game", None, TitleRef("movie", "oppenheimer")),
        ("games/elden-ring", None, None, TitleRef("game", "elden-ring")),
        ("tv/the-bear/season-3", None, None, TitleRef("tv", "the-bear", "season-3")),
        ("tv/the-bear", None, 2, TitleRef("tv", "the-bear", "season-2")),
        ("the-bear", "tv", "specials", TitleRef("tv", "the-bear", "specials")),
        (
            "https://www.metacritic.com/game/elden-ring/critic-reviews/?platform=pc",
            None,
            None,
            TitleRef("game", "elden-ring"),
        ),
        (
            "https://www.metacritic.com/tv/the-bear/season-3/",
            None,
            None,
            TitleRef("tv", "the-bear", "season-3"),
        ),
        ("www.metacritic.com/movie/dune-part-two", None, None, TitleRef("movie", "dune-part-two")),
    ],
)
def test_parse_ref(ref, media, season, expected):
    assert parse_ref(ref, media, season) == expected


def test_title_ref_url():
    assert TitleRef("game", "elden-ring").url == "https://www.metacritic.com/game/elden-ring/"
    assert (
        TitleRef("tv", "the-bear", "season-3").url
        == "https://www.metacritic.com/tv/the-bear/season-3/"
    )


@pytest.mark.parametrize(
    ("ref", "kwargs"),
    [
        ("", {}),
        ("https://example.com/game/elden-ring/", {}),
        ("elden-ring", {"season": 2}),
        ("Elden Ring!", {}),
        ("tv/the-bear", {"season": "finale"}),
    ],
)
def test_parse_ref_rejects(ref, kwargs):
    with pytest.raises(ValueError):
        parse_ref(ref, **kwargs)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(3, "season-3"), ("3", "season-3"), ("Season 3", "season-3"), ("0", "specials"), (None, None)],
)
def test_season_slug(value, expected):
    assert season_slug(value) == expected


def test_browse_url():
    assert browse_url("game", "all-time", "metascore", []) == (
        "https://www.metacritic.com/browse/game/all/all/all-time/metascore/"
    )
    url = browse_url(
        "games",
        "2025",
        "userscore",
        [("platform", "ps5"), ("genre", "Party / Minigame")],
        page=3,
    )
    assert url == (
        "https://www.metacritic.com/browse/game/all/all/2025/userscore/"
        "?platform=ps5&genre=Party%20%2F%20Minigame&page=3"
    )


def test_reviews_url_for_each_media():
    game = reviews_url(TitleRef("game", "elden-ring"), "critic", platform="pc", sort="date")
    assert game == (
        "https://backend.metacritic.com/reviews/metacritic/critic/games/elden-ring/platform/pc/web"
        "?offset=0&limit=10&filterBySentiment=all&sort=date"
    )
    movie = reviews_url(TitleRef("movie", "oppenheimer"), "user", offset=100, limit=100)
    assert movie.endswith(
        "/user/movies/oppenheimer/web?offset=100&limit=100&filterBySentiment=all&sort=date"
    )
    show = reviews_url(TitleRef("tv", "the-bear"), "critic")
    assert "/critic/shows/the-bear/web?" in show and show.endswith("sort=score")
    season = reviews_url(TitleRef("tv", "the-bear", "season-3"), "critic", sentiment="negative")
    assert "/critic/seasons/the-bear/season/season-3/web?" in season
    assert "filterBySentiment=negative" in season


def test_search_url():
    assert search_url("elden ring", "game", 30, 30) == (
        "https://backend.metacritic.com/finder/metacritic/search/elden%20ring/web"
        "?offset=30&limit=30&mcoTypeId=13"
    )
    assert "mcoTypeId=1%2C2%2C3%2C13" in search_url("zelda")


def test_image_url():
    assert image_url("/provider/6/3/6-1-4763-13.jpg") == (
        "https://www.metacritic.com/a/img/catalog/provider/6/3/6-1-4763-13.jpg"
    )
    assert image_url(None) is None
    assert image_url("https://cdn.example/x.jpg") == "https://cdn.example/x.jpg"
