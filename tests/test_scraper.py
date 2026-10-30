from __future__ import annotations

import copy
import json

import pytest
from conftest import by_url, feed, fixture_json, fixture_text, nuxt_page, page, sequence
from scrapeunblocker.exceptions import (
    AuthenticationError,
    BlockedError,
    RateLimitError,
    ScrapeTimeoutError,
    TargetNotFoundError,
)

from metacritic_scraper import BrowseFilters, FilterError, NotFoundError, ParseError
from metacritic_scraper.scraper import ignored_filters


def test_retries_transient_errors_with_backoff(make_mc):
    sleeps = []
    mc, client = make_mc(
        sequence(
            RateLimitError("slow down", status_code=429),
            ScrapeTimeoutError("timeout"),
            BlockedError("blocked", status_code=403),
            page("browse_game.json"),
        ),
        sleep=sleeps.append,
        backoff=1.5,
    )
    result = mc.browse_page("game")
    assert len(result.titles) == 3
    assert sleeps == [1.5, 3.0, 6.0]
    assert mc.requests == 4
    assert client.calls[0] == (
        "https://www.metacritic.com/browse/game/all/all/all-time/metascore/",
        {"proxy_country": "us"},
    )


def test_gives_up_after_max_retries(make_mc):
    mc, client = make_mc(sequence(RateLimitError("slow down", status_code=429)), max_retries=2)
    with pytest.raises(RateLimitError):
        mc.browse_page("game")
    assert len(client.calls) == 3


def test_not_found_is_not_retried(make_mc):
    missing = TargetNotFoundError("gone", status_code=404, origin_status=404)
    mc, client = make_mc(sequence(missing))
    with pytest.raises(NotFoundError):
        mc.title("no-such-game")
    assert len(client.calls) == 1


def test_auth_errors_are_raised_at_once(make_mc):
    mc, client = make_mc(sequence(AuthenticationError("bad key", status_code=401)))
    with pytest.raises(AuthenticationError):
        mc.title("elden-ring")
    assert len(client.calls) == 1


def test_bad_page_is_fetched_once_more(make_mc):
    blocked = "<html><body>Just a moment...</body></html>"
    mc, client = make_mc(sequence(blocked, page("title_game.json")))
    assert mc.title("elden-ring").metascore == 96
    assert len(client.calls) == 2

    mc, client = make_mc(sequence(blocked))
    with pytest.raises(ParseError):
        mc.title("elden-ring")
    assert len(client.calls) == 2


def test_proxy_country_can_be_left_to_the_api(make_mc):
    mc, client = make_mc(sequence(page("browse_game.json")), proxy_country=None)
    mc.browse_page("game")
    assert client.calls[0][1] == {}


def test_browse_reads_pages_and_stops_at_the_end(make_mc):
    mc, client = make_mc(sequence(page("browse_game.json")))
    filters = BrowseFilters(platforms=["ps5", "pc"], genres=["rpg"], year_from=2020, year_to=2025)
    result = mc.browse("game", filters, pages=5)
    # 42 titles = 2 pages of 24; the fake answers the same three titles each time.
    assert result.pages_fetched == 2 and len(client.calls) == 2
    assert result.total == 42
    assert [t.title for t in result.titles] == ["Kynseed", "Omori", "Arco"]
    assert result.ignored_filters == []
    assert client.urls[0] == (
        "https://www.metacritic.com/browse/game/all/all/all-time/metascore/"
        "?releaseYearMin=2020&releaseYearMax=2025&platform=ps5&platform=pc&genre=RPG"
    )
    assert client.urls[1].endswith("&genre=RPG&page=2")


def test_browse_limit_and_score_floors(make_mc):
    mc, client = make_mc(sequence(page("browse_game.json")))
    assert [t.title for t in mc.browse("game", limit=2).titles] == ["Kynseed", "Omori"]
    result = mc.browse("game", min_metascore=88, min_user_score=8)
    assert [t.title for t in result.titles] == ["Omori"]
    result = mc.browse("game", start_page=2)
    assert client.urls[-1].endswith("/metascore/?page=2")
    assert result.titles[0].rank == 25


def test_browse_reports_an_ignored_platform_filter(make_mc):
    mc, _ = make_mc(sequence(page("browse_unfiltered.json")))
    result = mc.browse("game", BrowseFilters(platforms=["ps5"]))
    assert result.ignored_filters == [("platform", "ps5")]


def test_ignored_filters_for_streaming_services():
    from metacritic_scraper.parsing import parse_browse

    titles = parse_browse(page("browse_movie.json")).titles
    assert ignored_filters(BrowseFilters(networks=["netflix"]), "movie", titles) == []
    assert ignored_filters(BrowseFilters(networks=["hulu"]), "movie", titles) == [
        ("network", "hulu")
    ]
    assert ignored_filters(BrowseFilters(genres=["Drama"]), "movie", titles) == []
    assert ignored_filters(None, "movie", titles) == []


def test_browse_validates_before_any_request(make_mc):
    mc, client = make_mc(sequence(page("browse_game.json")))
    with pytest.raises(FilterError):
        mc.browse("game", BrowseFilters(platforms=["ps6"]))
    with pytest.raises(FilterError):
        mc.browse("movie", BrowseFilters(platforms=["ps5"]))
    assert client.calls == []


def test_browse_dedupes_repeated_titles(make_mc):
    state = fixture_json("browse_game.json")
    key = next(iter(state["data"]))
    items = state["data"][key]["items"]
    state["data"][key]["items"] = items + [copy.deepcopy(items[0])]
    mc, _ = make_mc(sequence(nuxt_page(state)))
    assert [t.title for t in mc.browse("game").titles] == ["Kynseed", "Omori", "Arco"]


def test_title_urls(make_mc):
    mc, client = make_mc(
        by_url(
            {
                "/game/elden-ring/": page("title_game.json"),
                "/movie/oppenheimer/": page("title_movie.json"),
                "/tv/the-bear/season-3/": page("title_season.json"),
            }
        )
    )
    assert mc.title("elden-ring").title == "Elden Ring"
    assert mc.title("oppenheimer", "movie").runtime_minutes == 180
    assert mc.title("tv/the-bear", season=3).season == 3
    assert mc.title("https://www.metacritic.com/tv/the-bear/season-3/").metascore == 80
    assert client.urls == [
        "https://www.metacritic.com/game/elden-ring/",
        "https://www.metacritic.com/movie/oppenheimer/",
        "https://www.metacritic.com/tv/the-bear/season-3/",
        "https://www.metacritic.com/tv/the-bear/season-3/",
    ]


def _critic_items(start: int, count: int) -> list[dict]:
    return [
        {
            "quote": f"review {n}",
            "score": 90,
            "url": f"https://example.com/review/{n}",
            "date": "2022-02-23",
            "publicationName": f"Outlet {n}",
            "publicationSlug": f"outlet-{n}",
            "platform": "PC",
        }
        for n in range(start, start + count)
    ]


def test_critic_reviews_page_through_offsets(make_mc):
    def respond(url: str) -> str:
        offset = int(url.split("offset=")[1].split("&")[0])
        return feed(25, _critic_items(offset, min(10, 25 - offset)))

    mc, client = make_mc(respond)
    result = mc.reviews("elden-ring", platform="ps5", sort="newest", limit=None)
    assert (result.total, len(result.reviews), result.requests) == (25, 25, 3)
    assert result.kind == "critic" and result.title == "https://www.metacritic.com/game/elden-ring/"
    assert [r.publication for r in result.reviews][:2] == ["Outlet 0", "Outlet 1"]
    assert client.urls[0] == (
        "https://backend.metacritic.com/reviews/metacritic/critic/games/elden-ring"
        "/platform/playstation-5/web?offset=0&limit=10&filterBySentiment=all&sort=date"
    )
    assert "offset=10&" in client.urls[1] and "offset=20&" in client.urls[2]


def test_reviews_stop_at_the_limit(make_mc):
    mc, client = make_mc(sequence(feed(500, _critic_items(0, 10))))
    result = mc.reviews("elden-ring", limit=15)
    assert len(result.reviews) == 10  # the fake repeats page 1; duplicates are dropped
    mc, client = make_mc(
        lambda url: feed(500, _critic_items(int(url.split("offset=")[1].split("&")[0]), 10))
    )
    result = mc.reviews("elden-ring", limit=15)
    assert len(result.reviews) == 15 and len(client.calls) == 2


def test_user_reviews_use_large_pages(make_mc):
    mc, client = make_mc(sequence(fixture_text("reviews_user.json")))
    result = mc.reviews("movie/oppenheimer", kind="user", sentiment="negative", limit=3, offset=40)
    assert [r.author for r in result.reviews] == ["5aurus", "Shoeb", "Lemur123y"]
    assert client.urls == [
        "https://backend.metacritic.com/reviews/metacritic/user/movies/oppenheimer/web"
        "?offset=40&limit=100&filterBySentiment=negative&sort=date"
    ]


def test_season_reviews_and_empty_feeds(make_mc):
    mc, client = make_mc(sequence(feed(0, [])))
    result = mc.reviews("tv/the-bear", season="3", sentiment="mixed")
    assert result.reviews == [] and result.total == 0
    assert "/critic/seasons/the-bear/season/season-3/web?" in client.urls[0]
    assert "filterBySentiment=neutral" in client.urls[0]


def test_reviews_validate_arguments(make_mc):
    mc, client = make_mc(sequence(feed(0, [])))
    with pytest.raises(ValueError):
        mc.reviews("movie/oppenheimer", platform="pc")
    with pytest.raises(FilterError):
        mc.reviews("elden-ring", kind="user", sort="publication")
    with pytest.raises(FilterError):
        mc.reviews("elden-ring", sentiment="angry")
    with pytest.raises(FilterError):
        mc.reviews("elden-ring", kind="press")
    assert client.calls == []


def test_unknown_review_platform_is_a_not_found(make_mc):
    missing = TargetNotFoundError("gone", status_code=404, origin_status=404)
    mc, client = make_mc(sequence(missing))
    with pytest.raises(NotFoundError):
        mc.reviews("elden-ring", platform="dreamcast")
    assert "/platform/dreamcast/web" in client.urls[0]


def test_search_pages_and_ranks(make_mc):
    body = json.loads(fixture_text("search.json"))
    calls = []

    def respond(url: str) -> str:
        calls.append(url)
        return json.dumps(body)

    mc, _ = make_mc(respond)
    result = mc.search("zelda", "games", limit=5)
    assert (result.query, result.kind, result.total) == ("zelda", "game", 103)
    assert [r.rank for r in result.results] == [1, 2, 3, 4, 5]
    assert len(calls) == 2
    assert calls[0].endswith("/search/zelda/web?offset=0&limit=30&mcoTypeId=13")
    assert "offset=3&" in calls[1]


def test_search_stops_at_total(make_mc):
    mc, client = make_mc(sequence(feed(2, [{"typeId": 2, "title": "Dune", "slug": "dune"}] * 2)))
    result = mc.search("dune", "movie", limit=None)
    assert len(result.results) == 2 and len(client.calls) == 1
    assert result.results[0].url == "https://www.metacritic.com/movie/dune/"
    with pytest.raises(ValueError):
        mc.search("  ")
