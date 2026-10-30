"""Turn Metacritic pages and JSON feeds into the typed models.

Title and browse pages carry their data in the Nuxt payload (see :mod:`.nuxt`) as a
list of named components (``product``, ``critic-score-summary``, ``game-stats``,
``where-to-watch``, ...). Reviews and search come from the JSON feeds those pages
load, which answer ``{"data": {"totalResults": ..., "items": [...]}}``.
"""

from __future__ import annotations

import html as html_lib
import json
import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .errors import NotFoundError, ParseError
from .models import (
    Award,
    BrowsePage,
    Bucket,
    Credit,
    Episode,
    Offer,
    PlatformScore,
    PlayerStats,
    Review,
    ReviewsPage,
    Season,
    Title,
    TitleDetails,
)
from .nuxt import NuxtDataError, extract
from .urls import BASE_URL, absolute, image_url

# Metacritic's content type ids.
_MEDIA_BY_TYPE_ID = {13: "game", 2: "movie", 1: "tv", 5: "tv", 3: "person", 31: "music"}
_MEDIA_BY_TYPE = {
    "game-title": "game",
    "games": "game",
    "movie": "movie",
    "movies": "movie",
    "show": "tv",
    "shows": "tv",
    "season": "tv",
    "seasons": "tv",
    "person": "person",
}
_BADGES = {"game": ("mustPlay", "Must-Play"), "movie": ("mustSee", "Must-See")}
_BADGES["tv"] = ("mustWatch", "Must-Watch")
_OFFER_KINDS = {"flatrate": "subscription", "ads": "free with ads"}
_PRE_RE = re.compile(r"<pre[^>]*>(.*)</pre>", re.S | re.I)


# -- helpers ----------------------------------------------------------------------------


def _int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _names(items: Any, key: str = "name") -> list[str]:
    out: list[str] = []
    for item in items or []:
        name = _text(item.get(key)) if isinstance(item, dict) else _text(item)
        if name and name not in out:
            out.append(name)
    return out


def _score(value: Any) -> int | float | None:
    number = _float(value)
    if number is None:
        return None
    return int(number) if number.is_integer() else number


def score_gap(metascore: Any, user_score: Any) -> float | None:
    """Metascore minus the user score scaled to 100 (``96`` and ``8.4`` -> ``12.0``)."""
    if metascore is None or user_score is None:
        return None
    return round(float(metascore) - float(user_score) * 10, 1)


def _media(item: dict[str, Any]) -> str:
    media = _MEDIA_BY_TYPE_ID.get(_int(item.get("typeId")) or -1)
    return media or _MEDIA_BY_TYPE.get(str(item.get("type") or ""), "unknown")


def _image(item: dict[str, Any]) -> str | None:
    images = [i for i in item.get("images") or [] if isinstance(i, dict)]
    preferred = [i for i in images if i.get("typeName") == "cardImage"]
    single = item.get("image") if isinstance(item.get("image"), dict) else None
    for image in [*preferred, *([single] if single else []), *images]:
        url = image_url(image.get("bucketPath") or image.get("imageUrl"))
        if url:
            return url
    return None


def _title_url(media: str, item: dict[str, Any]) -> str:
    season = item.get("season") if isinstance(item.get("season"), dict) else None
    if season and season.get("url"):
        return absolute(season["url"]) or ""
    path = {"game": "game", "movie": "movie", "tv": "tv", "person": "person"}.get(media, media)
    return f"{BASE_URL}/{path}/{item.get('slug')}/"


def _api_data(body: str) -> dict[str, Any]:
    """The ``data`` object of a JSON feed response (raw or wrapped in ``<pre>``)."""
    text = (body or "").strip()
    if text.startswith("<"):
        match = _PRE_RE.search(text)
        if not match:
            raise ParseError("expected JSON, got an HTML page")
        text = html_lib.unescape(match.group(1)).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        raise ParseError("the response is not valid JSON") from None
    if not isinstance(payload, dict):
        raise ParseError("unexpected JSON response")
    errors = payload.get("errors")
    if errors:
        first = errors[0] if isinstance(errors, list) and errors else {}
        code = _int(first.get("code")) if isinstance(first, dict) else None
        message = first.get("message") if isinstance(first, dict) else str(errors)
        if code == 404:
            raise NotFoundError(f"Metacritic has no such title or review list ({message})")
        raise ParseError(f"Metacritic answered {code or 'an error'}: {message}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ParseError("the JSON response has no data")
    return data


def page_state(html: str) -> dict[str, Any]:
    """The decoded Nuxt state of a Metacritic page."""
    try:
        state = extract(html)
    except NuxtDataError as exc:
        raise ParseError(f"not a Metacritic page ({exc})") from None
    if not isinstance(state, dict) or not isinstance(state.get("data"), dict):
        raise ParseError("the page data has an unexpected shape")
    return state


def page_components(state: dict[str, Any]) -> dict[str, Any]:
    """``{component name: data}`` for the main content of a title or search page."""
    out: dict[str, Any] = {}
    for key, value in state["data"].items():
        if not key.startswith("loadPage:") or "skeleton" in key or not isinstance(value, dict):
            continue
        for component in value.get("components") or []:
            if not isinstance(component, dict):
                continue
            name = (component.get("meta") or {}).get("componentName")
            if name and name not in out:
                out[name] = component.get("data")
    return out


# -- titles in lists --------------------------------------------------------------------


def title_from_item(
    item: dict[str, Any], *, rank: int | None = None, page: int | None = None
) -> Title:
    """A browse-list or search-result entry as a :class:`Title`."""
    media = _media(item)
    critic = item.get("criticScoreSummary") or {}
    user = item.get("userScore") or {}
    metascore = _int(critic.get("score"))
    user_score = _score(user.get("score")) if isinstance(user, dict) else None
    season = item.get("season") if isinstance(item.get("season"), dict) else {}
    seasons = _int(item.get("numberOfSeasons"))
    if seasons is None:
        seasons = _int(item.get("seasonCount"))
    badge = None
    if media in _BADGES and item.get(_BADGES[media][0]):
        badge = _BADGES[media][1]
    runtime = _int(item.get("duration")) if media == "movie" else None
    return Title(
        media=media,
        title=_text(item.get("title")) or "",
        slug=str(item.get("slug") or ""),
        url=_title_url(media, item),
        rank=rank,
        page=page,
        title_id=_int(item.get("id")),
        season=_int(season.get("number")),
        release_date=_text(item.get("releaseDate")),
        year=_int(item.get("premiereYear")),
        content_rating=_text(item.get("rating")),
        metascore=metascore,
        critic_review_count=_int(critic.get("reviewCount")),
        critic_positive=_int(critic.get("positiveCount")),
        critic_mixed=_int(critic.get("neutralCount")),
        critic_negative=_int(critic.get("negativeCount")),
        critic_sentiment=_text(critic.get("sentiment")),
        user_score=user_score,
        score_gap=score_gap(metascore, user_score),
        platforms=_names(item.get("platforms")),
        genres=_names(item.get("genres")),
        description=_text(item.get("description")),
        runtime_minutes=runtime or None,
        season_count=seasons if media == "tv" and seasons else None,
        must_badge=badge,
        image=_image(item),
    )


def parse_browse(html: str, *, url: str = "", page: int = 1) -> BrowsePage:
    """One page of a ``/browse/...`` list."""
    state = page_state(html)
    listing = next(
        (v for k, v in state["data"].items() if k.startswith("browse-") and isinstance(v, dict)),
        None,
    )
    if listing is None:
        raise ParseError("the page has no browse results")
    items = [i for i in listing.get("items") or [] if isinstance(i, dict)]
    start = (page - 1) * 24
    titles = [title_from_item(item, rank=start + n, page=page) for n, item in enumerate(items, 1)]
    return BrowsePage(url=url, page=page, total=_int(listing.get("total")), titles=titles)


# -- title pages ------------------------------------------------------------------------


def _buckets(rows: Any, order_key: str) -> list[Bucket]:
    rows = [r for r in rows or [] if isinstance(r, dict)]
    rows.sort(key=lambda r: _int(r.get(order_key)) or 0)
    return [Bucket(label=str(r.get("label") or ""), count=_int(r.get("total"))) for r in rows]


def _player_stats(data: Any) -> PlayerStats | None:
    item = (data or {}).get("item") if isinstance(data, dict) else None
    if not isinstance(item, dict):
        return None
    return PlayerStats(
        ratings=_buckets(item.get("ratings"), "game_rating_id"),
        play_time=_buckets(item.get("play_time"), "play_time"),
        difficulty=_buckets(item.get("difficulty"), "difficulty_id"),
        play_status=_buckets(item.get("play_status"), "play_status_id"),
    )


def _where_to_buy(data: Any) -> list[Offer]:
    offers: list[Offer] = []
    groups = data.get("items") if isinstance(data, dict) else None
    for group in groups or []:
        if not isinstance(group, dict):
            continue
        for option in group.get("groupOptions") or []:
            best = option.get("lowestPriceOption") if isinstance(option, dict) else None
            if not best:
                continue
            offers.append(
                Offer(
                    kind=str(best.get("purchaseType") or "buy").lower(),
                    store=_text(option.get("name")) or "",
                    platform=_text(group.get("groupName")),
                    price=_float(best.get("price")),
                    original_price=_float(best.get("originalPrice")),
                    discount_percent=_float(best.get("discountPercentage")),
                    currency="USD",
                    url=_text(best.get("linkUrl")),
                )
            )
    return offers


def _direct_link(url: Any) -> str | None:
    """The destination of a click-tracking link (its ``r=`` parameter), else the link."""
    link = _text(url)
    if not link:
        return None
    target = parse_qs(urlsplit(link).query).get("r")
    if target and target[0].startswith("http"):
        return target[0]
    return link


def _where_to_watch(data: Any) -> list[Offer]:
    item = (data or {}).get("item") if isinstance(data, dict) else None
    if not isinstance(item, dict):
        return []
    offers: list[Offer] = []
    for key in ("flatrate", "free", "ads", "rent", "buy"):
        for provider in item.get(key) or []:
            if not isinstance(provider, dict):
                continue
            options = [o for o in provider.get("options") or [] if isinstance(o, dict)] or [{}]
            for option in options:
                offers.append(
                    Offer(
                        kind=_OFFER_KINDS.get(key, key),
                        store=_text(provider.get("providerName")) or "",
                        price=_float(option.get("optionPrice")),
                        currency=_text(option.get("optionCurrencyCode")),
                        quality=_text(option.get("qualityType")),
                        url=_direct_link(provider.get("link")),
                    )
                )
    return offers


def _credits(people: Any, default_job: str | None = None) -> list[Credit]:
    out: list[Credit] = []
    for person in people or []:
        if not isinstance(person, dict) or not _text(person.get("name")):
            continue
        product = person.get("entertainmentProduct") or {}
        out.append(
            Credit(
                name=person["name"].strip(),
                job=_text(person.get("roleTypeGroupName")) or default_job,
                roles=_names(person.get("roles")),
                url=absolute(product.get("url")) if isinstance(product, dict) else None,
            )
        )
    return out


def _platforms(items: Any) -> list[PlatformScore]:
    out: list[PlatformScore] = []
    for item in items or []:
        if not isinstance(item, dict) or not _text(item.get("name")):
            continue
        summary = item.get("criticScoreSummary") or {}
        out.append(
            PlatformScore(
                name=item["name"].strip(),
                slug=_text(item.get("slug")),
                lead=bool(item.get("isLeadPlatform")),
                release_date=_text(item.get("releaseDate")),
                metascore=_int(summary.get("score")),
                critic_review_count=_int(summary.get("reviewCount")),
                critic_sentiment=_text(summary.get("sentiment")),
                url=absolute(summary.get("url")),
            )
        )
    out.sort(key=lambda p: not p.lead)
    return out


def _season(item: dict[str, Any]) -> Season:
    summary = item.get("criticScoreSummary") or {}
    return Season(
        number=_int(item.get("seasonNumber")),
        slug=_text(item.get("seasonSlug")) or _text(item.get("slug")),
        url=absolute(item.get("url")),
        year=_int(item.get("releaseYear")),
        premiere_date=_text(item.get("premiereDate")),
        episode_count=_int(item.get("totalEpisodes")),
        metascore=_int(summary.get("score")),
        critic_review_count=_int(summary.get("reviewCount")),
        critic_sentiment=_text(summary.get("sentiment")),
    )


def _episodes(items: Any) -> list[Episode]:
    return [
        Episode(
            number=_int(item.get("episodeNumber")),
            title=_text(item.get("title")) or "",
            release_date=_text(item.get("releaseDate")),
            runtime_minutes=_int(item.get("duration")) or None,
            content_rating=_text(item.get("rating")),
            description=_text(item.get("description")),
            url=absolute(item.get("url")),
        )
        for item in items or []
        if isinstance(item, dict)
    ]


def _item(data: Any) -> dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("item"), dict):
        return data["item"]
    return {}


def parse_title(html: str, *, url: str = "") -> TitleDetails:
    """A game, movie, TV show or TV season page."""
    components = page_components(page_state(html))
    product = _item(components.get("product"))
    if not product:
        raise ParseError("the page has no title data")
    media = _media(product)
    season_item = _item(components.get("season"))
    critic = _item(components.get("critic-score-summary"))
    product_critic = product.get("criticScoreSummary") or {}
    # On a season page the score summaries describe the season, not the show.
    headline = critic if season_item else (product_critic or critic)
    user = _item(components.get("user-score-summary"))
    user_reviews = components.get("user-reviews") or {}
    production = product.get("production") or {}
    companies = [c for c in production.get("companies") or [] if isinstance(c, dict)]
    metascore = _int(headline.get("score"))
    user_score = _score(user.get("score"))
    badge = None
    if media in _BADGES and product.get(_BADGES[media][0]):
        badge = _BADGES[media][1]

    details = TitleDetails(
        media=media,
        title=_text(product.get("title")) or "",
        slug=str(product.get("slug") or ""),
        url=url or _title_url(media, product),
        title_id=_int(product.get("id")),
        season=_int(season_item.get("seasonNumber")) if season_item else None,
        description=_text(product.get("description")),
        tagline=_text(product.get("tagline")),
        release_date=_text(season_item.get("premiereDate")) or _text(product.get("releaseDate")),
        year=_int(season_item.get("releaseYear")) or _int(product.get("premiereYear")),
        content_rating=_text(product.get("rating")),
        genres=_names(product.get("genres")),
        metascore=metascore,
        critic_review_count=_int(headline.get("reviewCount")),
        critic_positive=_int(critic.get("positiveCount", headline.get("positiveCount"))),
        critic_mixed=_int(critic.get("neutralCount", headline.get("neutralCount"))),
        critic_negative=_int(critic.get("negativeCount", headline.get("negativeCount"))),
        critic_sentiment=_text(critic.get("sentiment")) or _text(headline.get("sentiment")),
        user_score=user_score,
        user_rating_count=_int(user.get("reviewCount")),
        user_review_count=_int(user_reviews.get("totalResults"))
        if isinstance(user_reviews, dict)
        else None,
        user_positive=_int(user.get("positiveCount")),
        user_mixed=_int(user.get("neutralCount")),
        user_negative=_int(user.get("negativeCount")),
        user_sentiment=_text(user.get("sentiment")),
        score_gap=score_gap(metascore, user_score),
        must_badge=badge,
        image=_image(product),
    )
    if media == "game":
        details.platform = _text(product.get("platform"))
        details.platforms = _platforms(product.get("platforms"))
        details.developers = _names(c for c in companies if c.get("typeName") == "Developer")
        details.publishers = _names(c for c in companies if c.get("typeName") == "Publisher")
        details.franchises = _names((product.get("gameTaxonomy") or {}).get("franchises"))
        details.player_stats = _player_stats(components.get("game-stats"))
        details.where_to_buy = _where_to_buy(components.get("where-to-buy"))
    else:
        if media == "movie":
            details.runtime_minutes = _int(product.get("duration")) or None
        details.networks = _names(product.get("networks"))
        details.production_companies = _names(companies)
        details.cast = _credits(production.get("cast"), "Cast")
        details.crew = _credits(production.get("crew"))
        details.awards = [
            Award(
                event=str(a.get("awardEvent") or ""),
                wins=_int(a.get("wins")),
                nominations=_int(a.get("nominations")),
            )
            for a in product.get("awards") or []
            if isinstance(a, dict) and a.get("awardEvent")
        ]
        details.keywords = _names(product.get("tags"))
        details.imdb_id = _text(product.get("imdbId"))
        details.where_to_watch = _where_to_watch(components.get("where-to-watch"))
        if media == "tv":
            details.season_count = _int(product.get("seasonCount"))
            seasons = (components.get("seasons") or {}).get("items") or []
            details.seasons = [_season(s) for s in seasons if isinstance(s, dict)]
            details.episodes = _episodes((components.get("episodes") or {}).get("items"))
    return details


# -- JSON feeds -------------------------------------------------------------------------


def _review(item: dict[str, Any], kind: str) -> Review:
    product = item.get("reviewedProduct") or {}
    platform = item.get("platform")
    if isinstance(platform, dict):
        platform = platform.get("name")
    season = item.get("season")
    if isinstance(season, dict):
        season = season.get("name") or season.get("title")
    return Review(
        kind=kind,
        score=_score(item.get("score")),
        date=_text(item.get("date")),
        quote=_text(item.get("quote")),
        author=_text(item.get("author")),
        publication=_text(item.get("publicationName")),
        publication_slug=_text(item.get("publicationSlug")),
        url=_text(item.get("url")),
        review_id=_text(item.get("id")),
        platform=_text(platform),
        season=_text(str(season)) if season is not None else None,
        spoiler=item.get("spoiler") if isinstance(item.get("spoiler"), bool) else None,
        title=_text(product.get("title")) if isinstance(product, dict) else None,
        title_url=absolute(product.get("url")) if isinstance(product, dict) else None,
    )


def parse_reviews(body: str, *, kind: str, url: str = "", offset: int = 0) -> ReviewsPage:
    """One page of a critic or user review feed."""
    data = _api_data(body)
    items = [i for i in data.get("items") or [] if isinstance(i, dict)]
    return ReviewsPage(
        url=url,
        offset=offset,
        total=_int(data.get("totalResults")),
        reviews=[_review(i, kind) for i in items],
    )


def parse_search(body: str) -> tuple[int | None, list[Title]]:
    """``(total, results)`` from a search feed page."""
    data = _api_data(body)
    items = [i for i in data.get("items") or [] if isinstance(i, dict)]
    return _int(data.get("totalResults")), [title_from_item(i) for i in items]
