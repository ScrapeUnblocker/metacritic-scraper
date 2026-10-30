from __future__ import annotations

import csv
import io
import json

import pytest
from conftest import FakeClient, by_url, fixture_text, page

from metacritic_scraper import Metacritic, cli


@pytest.fixture
def fake_api(monkeypatch):
    """Route the CLI's Metacritic client to fixtures instead of the API."""
    client = FakeClient(
        by_url(
            {
                "/browse/game/": page("browse_game.json"),
                "/browse/movie/": page("browse_movie.json"),
                "/game/elden-ring/": page("title_game.json"),
                "/movie/oppenheimer/": page("title_movie.json"),
                "/reviews/metacritic/critic/": fixture_text("reviews_critic.json"),
                "/reviews/metacritic/user/": fixture_text("reviews_user.json"),
                "/finder/metacritic/search/": fixture_text("search.json"),
            }
        )
    )
    created = []

    def make(*args, **kwargs):
        kwargs["client"] = client
        kwargs["sleep"] = lambda seconds: None
        mc = Metacritic(*args, **kwargs)
        created.append(mc)
        return mc

    monkeypatch.setattr(cli, "Metacritic", make)
    return client


def test_parser_defaults_and_choices():
    parser = cli.build_parser()
    args = parser.parse_args(["browse", "games", "--platform", "ps5,pc", "--genre", "rpg"])
    assert (args.media, args.pages, args.start_page, args.sort) == ("game", 1, 1, None)
    assert cli._split(args.platform) == ["ps5", "pc"]
    args = parser.parse_args(["reviews", "elden-ring", "--user", "--sentiment", "mixed"])
    assert (args.kind, args.sentiment, args.limit, args.all) == ("user", "mixed", 100, False)
    assert parser.parse_args(["reviews", "x"]).kind == "critic"
    args = parser.parse_args(["title", "elden-ring", "movie/oppenheimer", "--type", "movies"])
    assert args.refs == ["elden-ring", "movie/oppenheimer"] and args.media == "movie"
    assert parser.parse_args(["search", "zelda"]).kind == "all"
    for bad in (
        ["browse", "music"],
        ["browse", "game", "--sort", "popular"],
        ["browse", "game", "-p", "0"],
        ["reviews", "x", "--user", "--critic"],
        ["search", "x", "--type", "music"],
        ["browse", "game", "--param", "novalue"],
    ):
        with pytest.raises(SystemExit):
            parser.parse_args(bad)


def test_browse_table(fake_api, capsys):
    code = cli.main(["browse", "game", "--platform", "ps5", "--year", "2025", "-f", "table"])
    out, err = capsys.readouterr()
    assert code == 0
    assert out.splitlines()[0].split()[:4] == ["rank", "title", "year", "metascore"]
    assert "Kynseed" in out
    assert "42 titles; 3 collected from 1 page(s)" in err
    assert "/browse/game/all/all/2025/metascore/?platform=ps5" in fake_api.urls[0]
    # The fixture lists PC games only, so the PS5 filter looks ignored.
    assert "warning: Metacritic ignored the filter platform=ps5" in err


def test_browse_csv_file(fake_api, tmp_path, capsys):
    target = tmp_path / "movies.csv"
    code = cli.main(["browse", "movie", "--network", "netflix", "-o", str(target)])
    assert code == 0
    rows = list(csv.DictReader(io.StringIO(target.read_text(encoding="utf-8"))))
    assert rows[2]["title"] == "Between the Temples"
    assert rows[2]["platforms"] == "Prime Video | Vudu | Netflix"
    assert "warning" not in capsys.readouterr().err


def test_title_json_and_table(fake_api, capsys):
    assert cli.main(["title", "elden-ring"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["metascore"] == 96 and data["platforms"][0]["slug"] == "playstation-5"
    assert cli.main(["title", "elden-ring", "movie/oppenheimer", "-f", "table"]) == 0
    out = capsys.readouterr().out
    assert "Elden Ring" in out and "Oppenheimer" in out


def test_reviews_jsonl(fake_api, capsys):
    assert cli.main(["reviews", "elden-ring", "--platform", "pc", "-n", "2", "-f", "jsonl"]) == 0
    out, err = capsys.readouterr()
    lines = [json.loads(line) for line in out.splitlines()]
    assert [r["publication"] for r in lines] == ["Cubed3", "Riot Pixels"]
    assert "2 of 63 critic review(s)" in err
    assert "/platform/pc/web?" in fake_api.urls[0]


def test_user_reviews_table(fake_api, capsys):
    assert cli.main(["reviews", "movie/oppenheimer", "--user", "-n", "3", "-f", "table"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].split()[:3] == ["date", "score", "author"]
    assert "5aurus" in out


def test_search(fake_api, capsys):
    assert cli.main(["search", "zelda", "--type", "game", "-n", "2", "-f", "csv"]) == 0
    out, err = capsys.readouterr()
    rows = list(csv.DictReader(io.StringIO(out)))
    assert [r["title"] for r in rows] == [
        "The Legend of Zelda: Tears of the Kingdom",
        "The Legend of Zelda: Breath of the Wild",
    ]
    assert "103 results for 'zelda' (game)" in err


def test_filters_listing_is_offline(fake_api, capsys):
    assert cli.main(["filters", "game", "--name", "platform", "-f", "csv"]) == 0
    rows = list(csv.DictReader(io.StringIO(capsys.readouterr().out)))
    assert rows[0] == {
        "filter": "platform",
        "value": "ps5",
        "label": "PS5",
        "shown_as": "PlayStation 5",
    }
    assert cli.main(["filters", "movie"]) == 0
    values = {(r["filter"], r["value"]) for r in json.loads(capsys.readouterr().out)}
    assert ("network", "netflix") in values and ("genre", "Drama") in values
    assert not any(f == "platform" for f, _ in values)
    assert fake_api.calls == []


def test_errors_exit_non_zero(fake_api, capsys):
    assert cli.main(["browse", "movie", "--platform", "ps5"]) == 1
    assert "error: platforms filter games" in capsys.readouterr().err
    assert cli.main(["reviews", "movie/oppenheimer", "--platform", "pc"]) == 1
    assert "error:" in capsys.readouterr().err
    assert cli.main(["title", "https://example.com/game/x/"]) == 1
    assert fake_api.calls == []
