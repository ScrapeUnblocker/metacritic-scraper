from __future__ import annotations

import json

import pytest
from conftest import fixture_text, nuxt_page, page

from metacritic_scraper import NotFoundError, ParseError, score_gap
from metacritic_scraper.parsing import (
    parse_browse,
    parse_reviews,
    parse_search,
    parse_title,
)


def test_browse_games():
    result = parse_browse(page("browse_game.json"), url="u", page=1)
    assert result.total == 42
    assert result.last_page == 2 and result.has_next
    first = result.titles[0]
    assert (first.rank, first.page, first.media, first.title) == (1, 1, "game", "Kynseed")
    assert first.url == "https://www.metacritic.com/game/kynseed/"
    assert (first.metascore, first.critic_review_count, first.user_score) == (89, 7, 7.5)
    assert first.critic_sentiment == "Generally favorable"
    assert first.score_gap == 14.0
    assert first.platforms == ["PC"] and first.genres == ["RPG"]
    assert first.image == "https://www.metacritic.com/a/img/catalog/provider/6/12/6-1-664696-52.jpg"
    assert first.runtime_minutes is None and first.season_count is None
    assert [t.title for t in result.titles] == ["Kynseed", "Omori", "Arco"]
    assert result.titles[1].user_score == 9


def test_browse_ranks_continue_on_later_pages():
    result = parse_browse(page("browse_game.json"), page=2)
    assert [t.rank for t in result.titles] == [25, 26, 27]
    assert not result.has_next


def test_browse_movies_list_streaming_services():
    result = parse_browse(page("browse_movie.json"))
    procession, _, temples = result.titles
    assert procession.media == "movie" and procession.runtime_minutes == 116
    assert procession.url == "https://www.metacritic.com/movie/procession/"
    assert temples.platforms == ["Prime Video", "Vudu", "Netflix"]
    assert temples.genres == ["Comedy", "Drama"]


def test_browse_tv_seasons_link_to_the_season():
    result = parse_browse(page("browse_tv.json"))
    nocturne, dexter = result.titles
    assert nocturne.media == "tv" and nocturne.season == 1
    assert nocturne.url == "https://www.metacritic.com/tv/nocturne-2026/season-1/"
    assert nocturne.user_score is None and nocturne.score_gap is None
    assert dexter.season == 2 and dexter.season_count == 2
    assert dexter.metascore == 75


def test_browse_without_list_raises():
    with pytest.raises(ParseError):
        parse_browse(nuxt_page({"path": "/", "data": {"other": {}}}))
    with pytest.raises(ParseError):
        parse_browse("<html><body>Access denied</body></html>")


def test_game_page():
    game = parse_title(page("title_game.json"), url="https://www.metacritic.com/game/elden-ring/")
    assert (game.media, game.title, game.slug) == ("game", "Elden Ring", "elden-ring")
    assert (game.metascore, game.critic_review_count, game.critic_sentiment) == (
        96,
        93,
        "Universal acclaim",
    )
    assert (game.critic_positive, game.critic_mixed, game.critic_negative) == (86, 0, 0)
    assert (game.user_score, game.user_rating_count, game.user_review_count) == (8.4, 24933, 6636)
    assert (game.user_positive, game.user_mixed, game.user_negative) == (20465, 1601, 2867)
    assert game.score_gap == 12.0
    assert game.must_badge == "Must-Play"
    assert game.content_rating == "M" and game.genres == ["Action RPG"]
    assert game.release_date == "2022-02-25" and game.year == 2022
    assert game.platform == "PlayStation 5"
    assert game.platforms[0].name == "PlayStation 5" and game.platforms[0].lead
    by_name = {p.name: p for p in game.platforms}
    assert by_name["PC"].slug == "pc" and by_name["PC"].metascore == 94
    assert by_name["PC"].critic_review_count == 63
    assert by_name["Xbox One"].metascore is None
    assert game.developers == ["From Software"]
    assert game.publishers == ["Bandai Namco Games", "From Software"]
    assert game.franchises == ["Elden Ring"]
    stats = game.player_stats
    assert stats is not None
    assert [b.label for b in stats.ratings][:2] == ["Unplayable", "Terrible"]
    assert stats.ratings[-1].label == "Flawless" and stats.ratings[-1].count == 376
    assert stats.play_time[0].label == "< 1 Hour"
    assert {b.label for b in stats.difficulty} >= {"Tough", "Unforgiving"}
    offer = game.where_to_buy[0]
    assert (offer.kind, offer.store, offer.platform, offer.price) == (
        "buy",
        "Amazon",
        "Xbox One",
        52.97,
    )
    assert offer.original_price == 59.95 and offer.discount_percent == 11.64
    assert game.cast == [] and game.where_to_watch == []
    assert game.image and game.image.endswith(".jpg")


def test_movie_page():
    movie = parse_title(page("title_movie.json"))
    assert movie.url == "https://www.metacritic.com/movie/oppenheimer/"
    assert (movie.media, movie.title, movie.runtime_minutes) == ("movie", "Oppenheimer", 180)
    assert movie.tagline == "The World Forever Changes"
    assert (movie.metascore, movie.critic_mixed, movie.user_score) == (90, 2, 8.4)
    assert movie.imdb_id == "tt15398776"
    assert movie.cast[0].name == "Cillian Murphy"
    assert movie.cast[0].roles == ["J. Robert Oppenheimer"]
    assert movie.cast[0].url == "https://www.metacritic.com/person/cillian-murphy/"
    assert movie.crew[0].name == "Christopher Nolan" and movie.crew[0].job == "Directed By"
    assert movie.awards[0].event == "Academy Awards, USA" and movie.awards[0].wins == 7
    assert movie.production_companies[0] == "Universal Pictures"
    assert movie.keywords[:2] == ["manhattan-project", "nuclear-physicist"]
    kinds = {o.kind for o in movie.where_to_watch}
    assert {"subscription", "rent"} <= kinds
    rent = next(o for o in movie.where_to_watch if o.kind == "rent")
    assert rent.price == 3.99 and rent.currency == "USD"
    # The click-tracking link is unwrapped to the store's own page.
    assert all("justwatch" not in (o.url or "") for o in movie.where_to_watch)
    assert movie.platforms == [] and movie.player_stats is None
    row = movie.to_row()
    assert row["directors"] == "Christopher Nolan"
    assert "cast" not in row and "description" not in row


def test_tv_season_page():
    season = parse_title(page("title_season.json"))
    assert (season.media, season.title, season.season) == ("tv", "The Bear", 3)
    # Scores describe the season, not the whole show.
    assert (season.metascore, season.critic_review_count) == (80, 45)
    assert (season.critic_positive, season.critic_mixed, season.critic_negative) == (37, 7, 1)
    assert season.release_date == "2024-06-26" and season.year == 2024
    assert season.networks == ["HULU"]
    assert season.season_count == 6
    assert [s.slug for s in season.seasons][:2] == ["specials", "season-1"]
    first = season.seasons[1]
    assert (first.number, first.metascore, first.episode_count) == (1, 88, 8)
    assert season.episodes[0].title == "Tomorrow"
    assert season.episodes[0].runtime_minutes == 37
    assert season.episodes[0].url == (
        "https://www.metacritic.com/tv/the-bear/season-3/episode-1-tomorrow/"
    )


def test_title_page_without_product_raises():
    with pytest.raises(ParseError):
        parse_title(nuxt_page({"path": "/", "data": {"loadPage:x:": {"components": []}}}))


def test_critic_reviews():
    result = parse_reviews(fixture_text("reviews_critic.json"), kind="critic", offset=10)
    assert (result.total, result.offset, len(result.reviews)) == (63, 10, 3)
    review = result.reviews[0]
    assert (review.kind, review.score, review.date) == ("critic", 70, "2022-08-29")
    assert (review.publication, review.platform) == ("Cubed3", "PC")
    assert review.url == "http://www.cubed3.com/review/6703/1/elden-ring-pc.html"
    assert review.author is None and review.review_id is None
    assert review.title == "Elden Ring"
    assert review.title_url == "https://www.metacritic.com/game/elden-ring/"
    assert review.quote.startswith("Elden Ring is an experience")


def test_user_reviews():
    result = parse_reviews(fixture_text("reviews_user.json"), kind="user")
    assert result.total == 580
    review = result.reviews[0]
    assert (review.kind, review.score, review.author) == ("user", 10, "5aurus")
    assert review.review_id == "02848947-99c7-47aa-ab0d-a97c3bc9c1c6"
    assert review.spoiler is False and review.url is None and review.publication is None


def test_season_reviews_name_the_season():
    result = parse_reviews(fixture_text("reviews_season.json"), kind="critic")
    assert result.reviews[0].title == "The Bear: Season 3"
    assert result.reviews[0].title_url == "https://www.metacritic.com/tv/the-bear/season-3/"


def test_search_results():
    total, results = parse_search(fixture_text("search.json"))
    assert total == 103
    first, _, person = results
    assert (first.media, first.title, first.metascore) == (
        "game",
        "The Legend of Zelda: Tears of the Kingdom",
        96,
    )
    assert first.must_badge == "Must-Play"
    assert first.platforms == ["Nintendo Switch"]
    assert first.url == "https://www.metacritic.com/game/the-legend-of-zelda-tears-of-the-kingdom/"
    assert person.media == "person" and person.url == "https://www.metacritic.com/person/zelda/"
    assert person.must_badge is None


def test_feed_errors():
    with pytest.raises(ParseError, match="400"):
        parse_reviews(fixture_text("api_error.json"), kind="critic")
    missing = json.dumps({"errors": [{"code": 404, "reason": "Not Found", "message": "nope"}]})
    with pytest.raises(NotFoundError):
        parse_search(missing)
    with pytest.raises(ParseError):
        parse_search("<html><body>blocked</body></html>")
    with pytest.raises(ParseError):
        parse_search("{not json")


def test_feed_wrapped_in_pre():
    body = (
        "<html><body><pre>"
        + fixture_text("search.json").replace("&", "&amp;")
        + "</pre></body></html>"
    )
    total, results = parse_search(body)
    assert total == 103 and len(results) == 3


def test_score_gap():
    assert score_gap(96, 8.4) == 12.0
    assert score_gap(70, 9.1) == -21.0
    assert score_gap(None, 8.0) is None
    assert score_gap(80, None) is None
