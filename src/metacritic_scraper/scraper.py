"""Scrape metacritic.com through the ScrapeUnblocker ``getPageSource`` API.

:class:`Metacritic` reads Metacritic's server-rendered pages and the JSON feeds those
pages load:

* :meth:`Metacritic.browse` - the browse lists for games, movies and TV shows, with
  Metacritic's platform, streaming-service, genre, year and sort filters, across pages;
* :meth:`Metacritic.title` - a game, movie, show or season page: Metascore and user
  score with their positive / mixed / negative split, per-platform scores, player
  stats, cast and crew, seasons and episodes, where to buy or watch;
* :meth:`Metacritic.reviews` - critic or user reviews, filtered and sorted, past the
  first page the site renders;
* :meth:`Metacritic.search` - Metacritic's search, per media type.

Throttled, blocked and timed-out requests are retried with doubling backoff. A
response without the expected data is fetched once more before :class:`ParseError`
is raised.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any, Callable

from .errors import NotFoundError, ParseError
from .models import (
    BrowsePage,
    BrowseResults,
    Review,
    ReviewResults,
    ReviewsPage,
    SearchResults,
    Title,
    TitleDetails,
)
from .options import (
    BrowseFilters,
    media_name,
    review_kind,
    review_platform,
    review_sort,
    search_type,
    sentiment_value,
)
from .parsing import parse_browse, parse_reviews, parse_search, parse_title
from .urls import TitleRef, browse_url, parse_ref, reviews_url, search_url

#: Metacritic serves critic reviews 10 at a time, whatever larger page is asked for.
CRITIC_PAGE_SIZE = 10
USER_PAGE_SIZE = 100
SEARCH_PAGE_SIZE = 30

_TRANSIENT_NAMES = (
    "UpstreamOutageError",
    "RateLimitError",
    "ScrapeTimeoutError",
    "BrowserTimeoutError",
    "BlockedError",
    "ServerError",
    "ConnectionError",
)
_NOT_FOUND_NAMES = ("TargetNotFoundError",)

log = logging.getLogger(__name__)


def _is_named(error: BaseException, *names: str) -> bool:
    return any(cls.__name__ in names for cls in type(error).__mro__)


class _BadPage(Exception):
    """A response without the expected data (fetched once more)."""


def ignored_filters(
    filters: BrowseFilters | None, media: str, titles: list[Title]
) -> list[tuple[str, str]]:
    """The platform / streaming-service filters Metacritic did not apply.

    Metacritic drops a filter value it does not know and returns the unfiltered
    list. When the filter is applied, every title lists one of the requested
    platforms (or services), so a title without any of them gives it away.
    """
    if filters is None or not titles:
        return []
    name, choices = filters.checked_choices(media)
    if not choices:
        return []
    wanted = {c.shown_as.lower() for c in choices}
    for title in titles:
        if not wanted & {p.lower() for p in title.platforms}:
            return [(name, c.slug) for c in choices]
    return []


def _review_key(review: Review) -> tuple[Any, ...]:
    if review.review_id:
        return (review.review_id,)
    return (review.publication_slug, review.date, review.url, (review.quote or "")[:80])


class Metacritic:
    """Read metacritic.com browse lists, title pages, reviews and search.

    Args:
        api_key: Your ScrapeUnblocker API key. Defaults to the
            ``SCRAPEUNBLOCKER_KEY`` environment variable (read by the SDK).
        client: A ready ``scrapeunblocker.Client`` (or anything with a compatible
            ``get_page_source``); handy for tests.
        proxy_country: Country to route requests through. ``"us"`` (the default)
            gets the US edition with US prices and streaming services.
        max_retries: Extra attempts for a request that fails transiently.
        backoff: Seconds before the first retry; doubles on each retry.
        timeout: Seconds to wait for one API response.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: Any = None,
        proxy_country: str | None = "us",
        max_retries: int = 3,
        backoff: float = 2.0,
        timeout: float = 180.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if client is None:
            from scrapeunblocker import Client

            client = Client(api_key=api_key, timeout=timeout)
        self.client = client
        self.proxy_country = proxy_country or None
        self.max_retries = max_retries
        self.backoff = backoff
        self.sleep = sleep
        #: Number of API requests made so far.
        self.requests = 0

    # -- fetching ----------------------------------------------------------------------

    def fetch(self, url: str, parse: Callable[[str], Any]) -> Any:
        """Fetch ``url`` and return ``parse(body)``, retrying transient failures.

        A 404 from Metacritic raises :class:`NotFoundError`. If ``parse`` raises
        :class:`ParseError` the page is fetched once more before the error is raised.
        """
        kwargs: dict[str, Any] = {}
        if self.proxy_country:
            kwargs["proxy_country"] = self.proxy_country
        attempt = 0
        bad_pages = 0
        while True:
            self.requests += 1
            try:
                try:
                    body = self.client.get_page_source(url, **kwargs)
                except Exception as exc:
                    if _is_named(exc, *_NOT_FOUND_NAMES):
                        raise NotFoundError(f"Metacritic answered 404 for {url}") from exc
                    raise
                try:
                    return parse(body if isinstance(body, str) else str(body))
                except ParseError as exc:
                    bad_pages += 1
                    if bad_pages > 1:
                        raise
                    raise _BadPage(str(exc)) from None
            except Exception as exc:
                retryable = isinstance(exc, _BadPage) or _is_named(exc, *_TRANSIENT_NAMES)
                if not retryable or attempt >= self.max_retries:
                    if isinstance(exc, _BadPage):
                        raise ParseError(f"{exc} ({url})") from None
                    raise
                reason = str(exc) if isinstance(exc, _BadPage) else type(exc).__name__
                log.info("retrying %s after %s", url, reason)
                self.sleep(self.backoff * (2**attempt))
                attempt += 1

    # -- browse lists ------------------------------------------------------------------

    def browse_url(self, media: str, filters: BrowseFilters | None = None, page: int = 1) -> str:
        """The metacritic.com URL of a browse page (validates the filters)."""
        time_segment, sort, params = (filters or BrowseFilters()).to_url_parts(media)
        return browse_url(media, time_segment, sort, params, page)

    def browse_page(
        self, media: str, filters: BrowseFilters | None = None, page: int = 1
    ) -> BrowsePage:
        """One page (24 titles) of a browse list.

        Args:
            media: ``game``, ``movie`` or ``tv``.
            filters: Platforms, streaming services, genres, release years and sort.
            page: 1-based page number.
        """
        url = self.browse_url(media, filters, page)
        return self.fetch(url, lambda html: parse_browse(html, url=url, page=page))

    def iter_browse(
        self,
        media: str,
        filters: BrowseFilters | None = None,
        *,
        pages: int = 1,
        start_page: int = 1,
    ) -> Iterator[BrowsePage]:
        """Browse pages from ``start_page`` on, stopping after ``pages`` pages or at the end."""
        for page in range(start_page, start_page + max(pages, 0)):
            result = self.browse_page(media, filters, page)
            yield result
            if not result.has_next:
                return

    def browse(
        self,
        media: str,
        filters: BrowseFilters | None = None,
        *,
        pages: int = 1,
        start_page: int = 1,
        limit: int | None = None,
        min_metascore: int | None = None,
        min_user_score: float | None = None,
    ) -> BrowseResults:
        """Titles from a browse list, across pages, de-duplicated.

        Args:
            media: ``game``, ``movie`` or ``tv``.
            filters: Platforms, streaming services, genres, release years and sort.
            pages: How many pages to read (24 titles each).
            start_page: First page to read.
            limit: Stop after this many titles.
            min_metascore: Keep titles with at least this Metascore (unscored ones are dropped).
            min_user_score: Keep titles with at least this user score (0-10).
        """
        media = media_name(media)
        titles: list[Title] = []
        seen: set[tuple[Any, ...]] = set()
        result: BrowseResults | None = None
        for page in self.iter_browse(media, filters, pages=pages, start_page=start_page):
            if result is None:
                result = BrowseResults(
                    url=page.url,
                    total=page.total,
                    titles=titles,
                    ignored_filters=ignored_filters(filters, media, page.titles),
                )
            result.pages_fetched += 1
            for title in page.titles:
                key = (title.title_id, title.season, title.slug)
                if key in seen:
                    continue
                seen.add(key)
                if min_metascore is not None and (title.metascore or -1) < min_metascore:
                    continue
                if min_user_score is not None and (
                    title.user_score is None or title.user_score < min_user_score
                ):
                    continue
                titles.append(title)
                if limit is not None and len(titles) >= limit:
                    return result
        if result is None:
            return BrowseResults(
                url=self.browse_url(media, filters, start_page), total=0, titles=[]
            )
        return result

    # -- title pages -------------------------------------------------------------------

    def title(
        self, ref: str, media: str | None = None, *, season: str | int | None = None
    ) -> TitleDetails:
        """A game, movie, TV show or season page.

        Args:
            ref: ``elden-ring``, ``movie/oppenheimer``, ``tv/the-bear/season-3`` or a
                metacritic.com URL.
            media: Media type for a bare slug (default ``game``).
            season: A TV season number (or ``specials``).
        """
        title_ref = parse_ref(ref, media, season)
        url = title_ref.url
        return self.fetch(url, lambda html: parse_title(html, url=url))

    # -- reviews -----------------------------------------------------------------------

    def reviews_page(
        self,
        ref: str | TitleRef,
        media: str | None = None,
        *,
        kind: str = "critic",
        sentiment: str = "all",
        sort: str | None = None,
        platform: str | None = None,
        season: str | int | None = None,
        offset: int = 0,
        page_size: int | None = None,
    ) -> ReviewsPage:
        """One page of a title's critic or user reviews, starting at ``offset``."""
        title_ref = ref if isinstance(ref, TitleRef) else parse_ref(ref, media, season)
        kind = review_kind(kind)
        size = page_size or (CRITIC_PAGE_SIZE if kind == "critic" else USER_PAGE_SIZE)
        url = reviews_url(
            title_ref,
            kind,
            platform=review_platform(platform),
            sentiment=sentiment_value(sentiment),
            sort=review_sort(sort, kind),
            offset=offset,
            limit=size,
        )
        return self.fetch(url, lambda body: parse_reviews(body, kind=kind, url=url, offset=offset))

    def reviews(
        self,
        ref: str,
        media: str | None = None,
        *,
        kind: str = "critic",
        sentiment: str = "all",
        sort: str | None = None,
        platform: str | None = None,
        season: str | int | None = None,
        limit: int | None = 100,
        offset: int = 0,
    ) -> ReviewResults:
        """A title's critic or user reviews across pages, de-duplicated.

        Args:
            ref: Title slug, ``media/slug`` or metacritic.com URL.
            media: Media type for a bare slug (default ``game``).
            kind: ``critic`` or ``user``.
            sentiment: ``all``, ``positive``, ``mixed`` or ``negative``.
            sort: ``score`` (critics' default), ``newest`` (users' default) or
                ``publication`` (critics only, A-Z).
            platform: For games, the platform whose reviews to read (``pc``, ``ps5``,
                ``xbox-series-x``, ...). Without it Metacritic returns the lead
                platform's reviews.
            season: For TV, one season's reviews.
            limit: Stop after this many reviews (``None`` reads them all).
            offset: Skip this many reviews first.
        """
        title_ref = parse_ref(ref, media, season)
        kind = review_kind(kind)
        # Validate before the first request.
        review_sort(sort, kind)
        sentiment_value(sentiment)
        if platform and title_ref.media != "game":
            raise ValueError("platform applies to game reviews only")
        before = self.requests
        out: list[Review] = []
        seen: set[tuple[Any, ...]] = set()
        total: int | None = None
        position = max(offset, 0)
        while limit is None or len(out) < limit:
            page = self.reviews_page(
                title_ref,
                kind=kind,
                sentiment=sentiment,
                sort=sort,
                platform=platform,
                offset=position,
            )
            total = page.total
            if not page.reviews:
                break
            for review in page.reviews:
                key = _review_key(review)
                if key in seen:
                    continue
                seen.add(key)
                out.append(review)
                if limit is not None and len(out) >= limit:
                    break
            position += len(page.reviews)
            if total is not None and position >= total:
                break
        return ReviewResults(
            title=title_ref.url,
            kind=kind,
            total=total,
            reviews=out,
            requests=self.requests - before,
        )

    # -- search ------------------------------------------------------------------------

    def search(
        self, query: str, kind: str = "all", *, limit: int | None = 30, offset: int = 0
    ) -> SearchResults:
        """Metacritic search results.

        Args:
            query: What to search for.
            kind: ``all``, ``game``, ``movie``, ``tv`` or ``person``.
            limit: Stop after this many results (``None`` reads them all).
            offset: Skip this many results first.
        """
        if not query or not query.strip():
            raise ValueError("a search query, e.g. 'zelda'")
        kind = search_type(kind)
        results: list[Title] = []
        total: int | None = None
        position = max(offset, 0)
        while limit is None or len(results) < limit:
            url = search_url(query, kind, position, SEARCH_PAGE_SIZE)
            total, items = self.fetch(url, parse_search)
            for number, item in enumerate(items, position + 1):
                item.rank = number
            results.extend(items)
            position += len(items)
            if not items or (total is not None and position >= total):
                break
        if limit is not None:
            results = results[:limit]
        return SearchResults(query=query.strip(), kind=kind, total=total, results=results)
