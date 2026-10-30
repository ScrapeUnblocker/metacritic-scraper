# Metacritic Scraper

[![CI](https://github.com/ScrapeUnblocker/metacritic-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/ScrapeUnblocker/metacritic-scraper/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Powered by ScrapeUnblocker](https://img.shields.io/badge/powered%20by-ScrapeUnblocker-ff6a00)](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos)

Scrape [Metacritic](https://www.metacritic.com) games, movies and TV shows into clean JSON or CSV: Metascores and user scores with their positive / mixed / negative split, per-platform scores, critic and user reviews, the browse charts with Metacritic's own filters (platform, streaming service, genre, year, sort), and search.

**Powered by [ScrapeUnblocker](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos)**: the `getPageSource` API fetches the Metacritic pages and the JSON feeds behind them, so this tool only has to read them.

## Why this exists

Metacritic is the reference for review scores across games, film and TV, which makes it a common source for game and media research, release tracking, recommendation datasets and review analysis. The data is spread over browse pages, title pages and review lists that only render the first 10 critic or 50 user reviews, and the browse filters have quirks: an unknown platform or service value is silently ignored and the unfiltered chart comes back. This package reads all of it, checks the filters and returns typed Python objects.

## Features

- **Browse charts** for games, movies and TV shows: best by Metascore, best by user score, or newest, with Metacritic's filters: 24 game platforms (`ps5`, `xbox-series-x`, `nintendo-switch-2`, `pc`, ...), 20 streaming services (`netflix`, `prime-video`, `disney-plus`, `hbo-max`, ...), game and film/TV genres, a release year or year range. Multiple pages, de-duplicated, with `--min-metascore` / `--min-user-score` floors.
- **Filter check**: every value is validated before a request is spent, and the results are checked against the filter (a title on another platform means Metacritic ignored it) so you get a warning instead of a silently unfiltered list.
- **Per title in a chart**: rank, title, URL, release date, year, content rating, Metascore with critic review count and positive / mixed / negative counts, sentiment ("Universal acclaim", ...), user score, the critics-vs-users **score gap**, platforms or streaming services, genres, description, runtime (movies), season (TV) and poster image.
- **Title pages** for games, movies, TV shows and single TV seasons: Metascore and user score with their full breakdowns, user rating and review counts, Must-Play badge, every platform's own Metascore and review slug, developers, publishers, franchises, player stats (play time, difficulty, completion, player rating distribution), where to buy with prices and discounts; for movies and TV: runtime, tagline, cast with roles, crew, production companies, awards, keywords, IMDb id, networks, seasons with their scores, episodes, and where to stream, rent or buy (direct store links).
- **Reviews** past what the page shows: critic reviews (score, publication, author, date, quote, link) and user reviews (score, author, date, text, spoiler flag), filtered by sentiment, sorted by score, date or publication, per game platform or TV season, as many as you ask for.
- **Search** across games, movies, TV shows and people, with paging.
- **Output**: JSON, JSON Lines, CSV (nested fields flattened) or a terminal table, from a CLI or as a Python library.
- **Resilient**: throttled, blocked and timed-out requests are retried with backoff; a response without Metacritic data is fetched once more.

## Install

```bash
git clone https://github.com/ScrapeUnblocker/metacritic-scraper.git
cd metacritic-scraper
pip install .
```

Python 3.9 or newer. The only runtime dependency is the official [`scrapeunblocker`](https://pypi.org/project/scrapeunblocker/) SDK.

Get an API key at [scrapeunblocker.com](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos) and put it in the environment (or copy `.env.example` to `.env` and load it your usual way):

```bash
export SCRAPEUNBLOCKER_KEY=your_key_here
```

## CLI

```bash
# The best-reviewed PS5 games of 2025
metacritic-scraper browse game --platform ps5 --year 2025 -n 20 -f table

# Action RPGs by user score, three pages, as CSV
metacritic-scraper browse game --genre "Action RPG" --sort userscore -p 3 -o rpgs.csv

# Netflix movies with a Metascore of 80+
metacritic-scraper browse movie --network netflix --min-metascore 80 -p 2 -f table

# Newest TV dramas since 2020
metacritic-scraper browse tv --genre drama --year-from 2020 --sort newest -o shows.jsonl

# Full title pages: a game, a movie, one TV season
metacritic-scraper title elden-ring -o elden-ring.json
metacritic-scraper title movie/oppenheimer -o oppenheimer.json
metacritic-scraper title tv/the-bear --season 3

# Critic reviews of the PC version, newest first
metacritic-scraper reviews elden-ring --platform pc --sort newest -n 30 -f table

# Negative user reviews of a movie
metacritic-scraper reviews movie/oppenheimer --user --sentiment negative -n 200 -o negative.csv

# Search, and the accepted filter values (offline)
metacritic-scraper search "zelda" --type game -f table
metacritic-scraper filters game --name platform -f table
```

| Command | What it returns |
| --- | --- |
| `browse` | A chart of `game`, `movie` or `tv` titles, with `--platform`, `--network`, `--genre`, `--year` / `--year-from` / `--year-to`, `--sort metascore\|userscore\|newest`, `--param NAME=VALUE`, `-p` pages, `--start-page`, `-n` limit, `--min-metascore`, `--min-user-score` |
| `title` | Full details for one or more titles (slug, `movie/slug`, `tv/slug/season-3` or a metacritic.com URL); `--type` for bare movie/TV slugs, `--season` |
| `reviews` | Critic (default) or `--user` reviews with `--sentiment all\|positive\|mixed\|negative`, `--sort score\|newest\|publication`, `--platform`, `--season`, `-n` (default 100), `--all`, `--offset` |
| `search` | Search results with `--type all\|game\|movie\|tv\|person`, `-n` |
| `filters` | The platform, streaming-service, genre and sort values `browse` accepts (no API call) |

Filter values:

| Option | Values |
| --- | --- |
| `--platform` (games) | `ps5`, `xbox-series-x`, `nintendo-switch-2`, `nintendo-switch`, `pc`, `mobile`, `ps4`, `xbox-one`, `ps3`, `xbox-360`, `wii-u`, `wii`, `3ds`, `nintendo-ds`, `ps-vita`, `psp`, `ps2`, `xbox`, `gamecube`, `game-boy-advance`, `ps1`, `nintendo-64`, `dreamcast`, `meta-quest` (names like `PS5` or `PlayStation 5` work too) |
| `--network` (movies, TV) | `netflix`, `prime-video`, `disney-plus`, `hbo-max`, `hulu`, `apple-tv`, `paramount-plus`, `peacock`, `amazon`, `itunes`, `vudu`, `youtube-premium`, `criterion-channel`, `discovery-plus`, `fubotv`, `plex`, `pluto`, `starz`, `sundance-now`, `tubi` |
| `--genre` | Games: `Action`, `Action RPG`, `RPG`, `Platformer`, `Roguelike`, `First-Person Shooter` (`fps`), `Strategy`, ... Movies and TV: `Drama`, `Comedy`, `Documentary`, `Sci-Fi`, `Horror`, ... Run `metacritic-scraper filters <media> --name genre` for the full lists |
| `--sort` | `metascore` (default), `userscore`, `newest` |

Common options: `-f json|jsonl|csv|table` (default: from the `-o` extension, else JSON), `-o FILE`, `--country` (proxy country, default `us`), `--retries`, `-v`. Run `metacritic-scraper <command> -h` for details.

### Example output

```text
$ metacritic-scraper browse game --platform ps5 --year 2025 -n 8 -f table
https://www.metacritic.com/browse/game/all/all/2025/metascore/?platform=ps5
235 titles; 8 collected from 1 page(s)
rank  title                               year  metascore  critic_review_count  user_score  score_gap  platforms      genres
1     Clair Obscur: Expedition 33         2025  92         86                   9.4         -2         PlayStation 5  JRPG
2     Hollow Knight: Silksong             2025  92         21                   8.6         6          PlayStation 5  Metroidvania
3     Forza Horizon 5                     2025  92         31                   6.7         25         PlayStation 5  Auto Racing Sim
4     Split Fiction                       2025  91         116                  8.6         5          PlayStation 5  Linear Action Adventure
5     Citizen Sleeper 2: Starward Vector  2025  90         10                                          PlayStation 5  Western RPG
6     Sektori                             2025  89         8                    6.9         20         PlayStation 5  Top-Down Shoot-'Em-Up
7     Death Stranding 2: On The Beach     2025  89         153                  8.7         2          PlayStation 5  Open-World Action
8     Dispatch                            2025  89         31                   9           -1         PlayStation 5  Adventure
```

`metacritic-scraper title elden-ring` (shortened: a selection of fields and list entries):

```json
{
  "media": "game",
  "title": "Elden Ring",
  "slug": "elden-ring",
  "url": "https://www.metacritic.com/game/elden-ring/",
  "release_date": "2022-02-25",
  "content_rating": "M",
  "genres": ["Action RPG"],
  "metascore": 96,
  "critic_review_count": 93,
  "critic_sentiment": "Universal acclaim",
  "user_score": 8.4,
  "user_rating_count": 24933,
  "user_review_count": 6636,
  "user_positive": 20465,
  "user_mixed": 1601,
  "user_negative": 2867,
  "score_gap": 12.0,
  "must_badge": "Must-Play",
  "platform": "PlayStation 5",
  "platforms": [
    {"name": "PlayStation 5", "slug": "playstation-5", "lead": true, "metascore": 96, "critic_review_count": 93},
    {"name": "PC", "slug": "pc", "lead": false, "metascore": 94, "critic_review_count": 63}
  ],
  "developers": ["From Software"],
  "publishers": ["Bandai Namco Games", "From Software"],
  "player_stats": {
    "difficulty": [
      {"label": "Simple", "count": 11},
      {"label": "Easy", "count": 8},
      {"label": "Just Right", "count": 66},
      {"label": "Tough", "count": 357},
      {"label": "Unforgiving", "count": 169}
    ]
  },
  "where_to_buy": [
    {"kind": "buy", "store": "Amazon", "platform": "Xbox One", "price": 52.97, "original_price": 59.95, "discount_percent": 11.64, "currency": "USD"}
  ]
}
```

```text
$ metacritic-scraper reviews elden-ring --platform pc --sort newest -n 5 -f table
5 of 63 critic review(s)
date        score  publication  platform  quote
2022-08-29  70     Cubed3       PC        Elden Ring is an experience that will n~
2022-04-28  82     Riot Pixels  PC        Elden Ring is massive, sometimes to its~
2022-04-14  90     RPGamer      PC        It’s hard to review Elden Ring without ~
2022-04-13  92     Ragequit.gr  PC        FromSoftware has opened up metaphorical~
2022-04-11  95     KeenGamer    PC        Every once in a while, a game comes aro~
```

`examples/critics_vs_players.py 2024`:

```text
48 of the top 72 games of 2024 have both scores

Critics liked more than players:
   +39.0  Metascore  84  users  4.5  Diablo IV: Vessel of Hatred (PC)
   +30.0  Metascore  85  users  5.5  World of Warcraft: The War Within (PC)
   +21.0  Metascore  86  users  6.5  Dragon's Dogma 2 (PlayStation 5)
   +16.0  Metascore  90  users  7.4  Tekken 8 (PlayStation 5)
   +16.0  Metascore  91  users  7.5  UFO 50 (PC)

Players liked more than critics:
    -4.0  Metascore  86  users  9.0  Silent Hill 2 (PlayStation 5)
    -2.0  Metascore  84  users  8.6  Broken Sword - Shadow of the Templars: Reforged (PC)
```

## Library

```python
from metacritic_scraper import BrowseFilters, Metacritic

mc = Metacritic()  # reads SCRAPEUNBLOCKER_KEY; or Metacritic(api_key="...")

# A browse chart with Metacritic's filters
best = mc.browse(
    "game",
    BrowseFilters(platforms=["ps5", "pc"], genres=["Action RPG"], year_from=2020),
    pages=2,
    min_user_score=8,
)
print(best.total, "games;", len(best.titles), "collected")
print(best.ignored_filters)  # [] when Metacritic applied every filter
for game in best.titles[:5]:
    print(game.rank, game.title, game.metascore, game.user_score, game.score_gap)

# Netflix movies, newest first
netflix = mc.browse("movie", BrowseFilters(networks=["netflix"], sort="newest"), limit=50)

# Full title pages
game = mc.title("elden-ring")
print(game.metascore, game.user_score, [(p.name, p.metascore) for p in game.platforms])
movie = mc.title("movie/oppenheimer")
print(movie.runtime_minutes, [c.name for c in movie.cast[:3]], movie.where_to_watch[:2])
season = mc.title("tv/the-bear", season=3)
print(season.metascore, [e.title for e in season.episodes])

# Reviews beyond the first page
critics = mc.reviews("elden-ring", platform="pc", sort="newest", limit=50)
users = mc.reviews("movie/oppenheimer", kind="user", sentiment="negative", limit=200)
print(critics.total, [r.publication for r in critics.reviews[:3]])
print(users.total, [(r.author, r.score) for r in users.reviews[:3]])

# Search
hits = mc.search("zelda", "game", limit=10)
print([(t.title, t.year, t.metascore) for t in hits.results])
```

`mc.browse_page(media, filters, page)` returns a single page, `mc.reviews_page(...)` a single review page with its total, and the parsers (`parse_browse`, `parse_title`, `parse_reviews`, `parse_search`) work on responses you already have.

### Fields

| Object | Fields |
| --- | --- |
| `Title` (browse, search) | `media`, `title`, `slug`, `url`, `rank`, `page`, `title_id`, `season`, `release_date`, `year`, `content_rating`, `metascore`, `critic_review_count`, `critic_positive`, `critic_mixed`, `critic_negative`, `critic_sentiment`, `user_score`, `score_gap`, `platforms`, `genres`, `description`, `runtime_minutes`, `season_count`, `must_badge`, `image` |
| `TitleDetails` | the score fields above plus `user_rating_count`, `user_review_count`, `user_positive`, `user_mixed`, `user_negative`, `user_sentiment`, `tagline`; games: `platform`, `platforms` (name, slug, lead, release date, Metascore, review count), `developers`, `publishers`, `franchises`, `player_stats`, `where_to_buy`; movies and TV: `runtime_minutes`, `networks`, `production_companies`, `cast`, `crew`, `awards`, `keywords`, `imdb_id`, `season_count`, `seasons`, `episodes`, `where_to_watch` |
| `Review` | `kind`, `score`, `date`, `quote`, `author`, `publication`, `publication_slug`, `url`, `review_id`, `platform`, `season`, `spoiler`, `title`, `title_url` |
| `Offer` | `kind` (buy, rent, subscription, free, free with ads), `store`, `platform`, `price`, `original_price`, `discount_percent`, `currency`, `quality`, `url` |

## Examples

| Script | What it does |
| --- | --- |
| [`examples/best_games_on_platform.py`](examples/best_games_on_platform.py) | The ten best-reviewed games of a year on one platform, as JSON |
| [`examples/critics_vs_players.py`](examples/critics_vs_players.py) | The biggest Metascore vs user score gaps among a year's top games |
| [`examples/reviews_to_csv.py`](examples/reviews_to_csv.py) | A title's critic and user reviews in two CSV files, with average scores |

## Good to know

- **Scores**: the Metascore is 0-100, the user score 0-10. `score_gap` puts both on the 100-point scale (`metascore - user_score * 10`): positive means critics liked the title more than users did.
- **Game platforms**: a game's Metascore and user score are those of its lead platform (`platform`, and `lead` in `platforms`). `platforms` lists every platform's own Metascore; pass one of their slugs (`pc`, `playstation-5`, `xbox-series-x`, ...) or a browse slug like `ps5` to `reviews --platform` for that version's reviews.
- **Review pages**: Metacritic serves critic reviews 10 per request; user reviews are read 100 at a time. So `reviews -n 100` costs 10 requests for critics and 1 for users.
- **Charts**: 24 titles per page. Sorting by `newest` includes titles that have no score yet. The TV `newest` chart lists individual seasons; they link to the season page.
- **Streaming services** filter movies well; Metacritic links far fewer TV shows to a service, so TV results with `--network` are short.
- **Empty genres**: some entries in Metacritic's own game genre menu (for example `Party / Minigame`) currently match no games on Metacritic itself, so they return an empty list.
- **Ignored filters**: an unknown filter value makes Metacritic return the unfiltered chart. The values are checked up front, and `browse` reports in `ignored_filters` (the CLI prints a warning) when the results do not match the platform or service you asked for.

## Project layout

```text
src/metacritic_scraper/
  scraper.py    Metacritic: fetching, retries, chart paging, titles, reviews, search
  parsing.py    browse pages, title pages and JSON feeds -> models
  nuxt.py       decoder for the __NUXT_DATA__ payload Metacritic pages carry
  models.py     Title, TitleDetails, Review, Offer, Season, ... dataclasses
  options.py    BrowseFilters and the accepted platforms, services, genres, sorts
  urls.py       metacritic.com URLs and title references
  export.py     JSON / JSONL / CSV / table output
  cli.py        the metacritic-scraper command
examples/       runnable scripts
tests/          offline tests with trimmed real responses (no API calls)
```

## Development

```bash
make install   # pip install -e ".[dev]"
make lint      # ruff check + ruff format --check
make test      # pytest (offline, the SDK is mocked)
make run       # a live call: the best PS5 games of 2025
```

## Links

- [ScrapeUnblocker](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos)
- [API documentation](https://docs.scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos)
- [Python SDK on PyPI](https://pypi.org/project/scrapeunblocker/)

This project is not affiliated with Metacritic. Use it in line with Metacritic's terms and applicable law.

## License

[MIT](LICENSE) © 2026 ScrapeUnblocker
