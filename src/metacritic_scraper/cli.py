"""``metacritic-scraper`` command line interface."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from typing import Any

from . import __version__
from .errors import MetacriticError
from .export import FORMATS, format_for, write
from .options import (
    GAME_GENRES,
    NETWORKS,
    PLATFORMS,
    REVIEW_SORTS,
    SCREEN_GENRES,
    SEARCH_TYPES,
    SENTIMENTS,
    SORTS,
    BrowseFilters,
    media_name,
)
from .scraper import Metacritic

EXAMPLES = """\
examples:
  metacritic-scraper browse game --platform ps5 --year 2025 -n 20 -f table
  metacritic-scraper browse game --genre "Action RPG" --sort userscore -p 3 -o rpgs.csv
  metacritic-scraper browse movie --network netflix --min-metascore 80 -p 2 -f table
  metacritic-scraper browse tv --genre drama --year-from 2020 --sort newest -o shows.jsonl
  metacritic-scraper title elden-ring -o elden-ring.json
  metacritic-scraper title movie/oppenheimer tv/the-bear --season 3 -f table
  metacritic-scraper reviews elden-ring --platform pc --sort newest -n 30 -f table
  metacritic-scraper reviews movie/oppenheimer --user --sentiment negative -n 200 -o neg.csv
  metacritic-scraper search "zelda" --type game -f table
  metacritic-scraper filters game --name platform -f table
"""

BROWSE_COLUMNS = (
    "rank",
    "title",
    "year",
    "metascore",
    "critic_review_count",
    "user_score",
    "score_gap",
    "platforms",
    "genres",
)
TITLE_COLUMNS = (
    "media",
    "title",
    "season",
    "year",
    "content_rating",
    "metascore",
    "critic_review_count",
    "user_score",
    "user_rating_count",
    "must_badge",
)
CRITIC_COLUMNS = ("date", "score", "publication", "platform", "quote")
USER_COLUMNS = ("date", "score", "author", "platform", "quote")
SEARCH_COLUMNS = ("rank", "media", "title", "year", "metascore", "platforms", "must_badge")
FILTER_COLUMNS = ("filter", "value", "label", "shown_as")


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return value


def media_arg(text: str) -> str:
    try:
        return media_name(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def key_value(text: str) -> tuple[str, str]:
    key, sep, value = text.partition("=")
    if not sep or not key.strip():
        raise argparse.ArgumentTypeError(f"expected NAME=VALUE, got {text!r}")
    return key.strip(), value.strip()


def _split(values: Sequence[str] | None) -> list[str]:
    """Repeatable, comma-separated option values as one flat list."""
    out: list[str] = []
    for value in values or []:
        out.extend(v.strip() for v in value.split(",") if v.strip())
    return out


def _output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-f",
        "--format",
        choices=FORMATS,
        help="output format (default: from the -o extension, else json)",
    )
    parser.add_argument("-o", "--output", help="write to this file instead of stdout")


def _media_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--type",
        dest="media",
        type=media_arg,
        help="media type for bare slugs: game (default), movie or tv",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="metacritic-scraper",
        description=(
            "Scrape Metacritic games, movies and TV shows - Metascores, user scores, "
            "reviews, browse lists and search - with the ScrapeUnblocker API."
        ),
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--country",
        default="us",
        help="proxy country for requests (default: us; 'any' lets the API choose)",
    )
    parser.add_argument(
        "--retries", type=int, default=3, help="retries for a failed request (default: 3)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="log requests and retries")
    sub = parser.add_subparsers(dest="command", required=True)

    browse = sub.add_parser(
        "browse",
        help="list games, movies or TV shows by Metascore, user score or release date",
        description="Read Metacritic's browse lists with its own filters.",
    )
    browse.add_argument("media", type=media_arg, help="game, movie or tv")
    browse.add_argument(
        "--platform",
        action="append",
        metavar="SLUG",
        help="game platform(s), comma-separated: ps5, xbox-series-x, nintendo-switch, pc, ...",
    )
    browse.add_argument(
        "--network",
        action="append",
        metavar="SLUG",
        help="streaming service(s) for movies/TV: netflix, prime-video, disney-plus, ...",
    )
    browse.add_argument(
        "--genre", action="append", metavar="NAME", help="genre(s), e.g. 'Action RPG' or drama"
    )
    browse.add_argument("--year", type=int, help="released in this year")
    browse.add_argument("--year-from", type=int, help="released in or after this year")
    browse.add_argument("--year-to", type=int, help="released in or before this year")
    browse.add_argument("--sort", choices=list(SORTS), help="sort order (default: metascore)")
    browse.add_argument(
        "--param",
        action="append",
        type=key_value,
        metavar="NAME=VALUE",
        help="any other query parameter, passed through",
    )
    browse.add_argument(
        "-p", "--pages", type=positive_int, default=1, help="pages to read (24 each)"
    )
    browse.add_argument("--start-page", type=positive_int, default=1, help="first page")
    browse.add_argument("-n", "--limit", type=positive_int, help="stop after this many titles")
    browse.add_argument("--min-metascore", type=int, help="keep titles with this Metascore or more")
    browse.add_argument(
        "--min-user-score", type=float, help="keep titles with this user score (0-10) or more"
    )
    _output_options(browse)

    title = sub.add_parser("title", help="full details for one or more titles")
    title.add_argument(
        "refs",
        nargs="+",
        metavar="TITLE",
        help="slug (elden-ring), media/slug (movie/oppenheimer) or metacritic.com URL",
    )
    _media_option(title)
    title.add_argument("--season", help="TV season number (or 'specials')")
    _output_options(title)

    reviews = sub.add_parser("reviews", help="critic or user reviews of a title")
    reviews.add_argument("ref", metavar="TITLE", help="slug, media/slug or metacritic.com URL")
    _media_option(reviews)
    who = reviews.add_mutually_exclusive_group()
    who.add_argument(
        "--critic", dest="kind", action="store_const", const="critic", help="critic reviews"
    )
    who.add_argument("--user", dest="kind", action="store_const", const="user", help="user reviews")
    reviews.add_argument("--sentiment", choices=list(SENTIMENTS), default="all")
    reviews.add_argument(
        "--sort",
        choices=list(REVIEW_SORTS),
        help="score (critics' default), newest (users' default), publication (critics)",
    )
    reviews.add_argument("--platform", help="game platform, e.g. pc, ps5, xbox-series-x")
    reviews.add_argument("--season", help="TV season number")
    reviews.add_argument(
        "-n", "--limit", type=positive_int, default=100, help="max reviews (default: 100)"
    )
    reviews.add_argument("--all", action="store_true", help="read every review (ignores -n)")
    reviews.add_argument("--offset", type=int, default=0, help="skip this many reviews first")
    reviews.set_defaults(kind="critic")
    _output_options(reviews)

    search = sub.add_parser("search", help="search Metacritic")
    search.add_argument("query", help="what to search for")
    search.add_argument("--type", dest="kind", choices=list(SEARCH_TYPES), default="all")
    search.add_argument(
        "-n", "--limit", type=positive_int, default=30, help="max results (default: 30)"
    )
    _output_options(search)

    filters = sub.add_parser(
        "filters", help="list the platform, streaming-service, genre and sort values (offline)"
    )
    filters.add_argument("media", type=media_arg, help="game, movie or tv")
    filters.add_argument(
        "--name",
        action="append",
        choices=["platform", "network", "genre", "sort"],
        help="only these filters",
    )
    _output_options(filters)
    return parser


def _note(message: str) -> None:
    print(message, file=sys.stderr)


def _utf8_streams() -> None:
    """Write UTF-8 when piped (Windows defaults to a legacy code page there)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            if stream.isatty():
                reconfigure(errors="replace")
            else:
                reconfigure(encoding="utf-8")
        except (OSError, ValueError):  # pragma: no cover - exotic streams
            pass


def browse_filters(args: argparse.Namespace) -> BrowseFilters:
    return BrowseFilters(
        platforms=_split(args.platform),
        networks=_split(args.network),
        genres=_split(args.genre),
        year=args.year,
        year_from=args.year_from,
        year_to=args.year_to,
        sort=args.sort,
        extra=args.param or [],
    )


def run_browse(mc: Metacritic, args: argparse.Namespace) -> Any:
    filters = browse_filters(args)
    filters.to_url_parts(args.media)  # validate before spending a request
    result = mc.browse(
        args.media,
        filters,
        pages=args.pages,
        start_page=args.start_page,
        limit=args.limit,
        min_metascore=args.min_metascore,
        min_user_score=args.min_user_score,
    )
    total = f"{result.total:,}" if result.total is not None else "?"
    _note(
        f"{result.url}\n{total} titles; {len(result.titles)} collected "
        f"from {result.pages_fetched} page(s)"
    )
    for name, value in result.ignored_filters:
        _note(f"warning: Metacritic ignored the filter {name}={value}")
    return result.titles


def run_reviews(mc: Metacritic, args: argparse.Namespace) -> Any:
    result = mc.reviews(
        args.ref,
        args.media,
        kind=args.kind,
        sentiment=args.sentiment,
        sort=args.sort,
        platform=args.platform,
        season=args.season,
        limit=None if args.all else args.limit,
        offset=args.offset,
    )
    total = f"{result.total:,}" if result.total is not None else "?"
    _note(f"{len(result.reviews)} of {total} {result.kind} review(s)")
    return result.reviews


def run_filters(args: argparse.Namespace) -> list[dict[str, Any]]:
    wanted = set(args.name or ["platform", "network", "genre", "sort"])
    rows: list[dict[str, Any]] = []
    if "platform" in wanted and args.media == "game":
        for c in PLATFORMS.values():
            rows.append(
                {"filter": "platform", "value": c.slug, "label": c.label, "shown_as": c.shown_as}
            )
    if "network" in wanted and args.media != "game":
        for c in NETWORKS.values():
            rows.append(
                {"filter": "network", "value": c.slug, "label": c.label, "shown_as": c.shown_as}
            )
    if "genre" in wanted:
        for genre in GAME_GENRES if args.media == "game" else SCREEN_GENRES:
            rows.append({"filter": "genre", "value": genre, "label": genre, "shown_as": None})
    if "sort" in wanted:
        for sort in SORTS:
            rows.append({"filter": "sort", "value": sort, "label": sort, "shown_as": None})
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _utf8_streams()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )
    fmt = format_for(args.output, args.format)
    country = None if args.country.lower() in {"any", "none", ""} else args.country.lower()
    try:
        columns: Sequence[str] | None = None
        if args.command == "filters":
            data: Any = run_filters(args)
            columns = FILTER_COLUMNS
        else:
            mc = Metacritic(proxy_country=country, max_retries=args.retries)
            if args.command == "browse":
                data = run_browse(mc, args)
                columns = BROWSE_COLUMNS
            elif args.command == "title":
                data = [mc.title(ref, args.media, season=args.season) for ref in args.refs]
                if len(data) == 1 and fmt == "json":
                    data = data[0]
                columns = TITLE_COLUMNS
            elif args.command == "reviews":
                data = run_reviews(mc, args)
                columns = CRITIC_COLUMNS if args.kind == "critic" else USER_COLUMNS
            else:
                result = mc.search(args.query, args.kind, limit=args.limit)
                total = f"{result.total:,}" if result.total is not None else "?"
                _note(f"{total} results for {result.query!r} ({result.kind})")
                data = result.results
                columns = SEARCH_COLUMNS
        write(data, fmt, args.output, columns=columns)
        if args.output:
            _note(f"wrote {args.output}")
    except (MetacriticError, ValueError) as exc:
        _note(f"error: {exc}")
        return 1
    except Exception as exc:  # SDK errors: auth, credits, outages
        _note(f"error: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
