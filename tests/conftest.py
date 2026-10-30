"""Shared test helpers: trimmed real Metacritic data and a fake ScrapeUnblocker client.

The fixtures are real responses cut down to a few entries each:

* ``browse_*.json`` - the decoded page state of browse lists: PS5 + PC RPGs from
  2020-2025, Netflix movies, new TV seasons, and the unfiltered games list Metacritic
  returns when it ignores a filter value;
* ``title_*.json`` - the decoded page state of Elden Ring, Oppenheimer and season 3
  of The Bear (score summaries, platforms, player stats, where to buy / watch,
  cast and crew, seasons, episodes);
* ``reviews_*.json``, ``search.json`` and ``api_error.json`` - JSON feed responses.

Title and browse pages arrive as HTML with a Nuxt ``__NUXT_DATA__`` payload;
:func:`nuxt_page` re-encodes a fixture state into such a page. No test calls the API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

from metacritic_scraper import Metacritic

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_json(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class Wrapped:
    """A devalue tagged value such as ``["ShallowReactive", <index>]``."""

    def __init__(self, tag: str, value: Any):
        self.tag = tag
        self.value = value


def to_devalue(value: Any) -> list[Any]:
    """Encode plain data the way Nuxt does: one flat array of values and indexes."""
    table: list[Any] = []

    def add(item: Any) -> int:
        index = len(table)
        table.append(None)
        if isinstance(item, Wrapped):
            table[index] = [item.tag, add(item.value)]
        elif isinstance(item, dict):
            table[index] = {key: add(child) for key, child in item.items()}
        elif isinstance(item, list):
            table[index] = [add(child) for child in item]
        else:
            table[index] = item
        return index

    add(value)
    return table


def nuxt_page(state: dict[str, Any]) -> str:
    """A minimal Metacritic page carrying ``state`` in its ``__NUXT_DATA__`` script."""
    root = Wrapped(
        "ShallowReactive",
        {
            "data": Wrapped("ShallowReactive", state["data"]),
            "state": {},
            "_errors": Wrapped("ShallowReactive", {}),
            "serverRendered": True,
            "path": state.get("path", "/"),
        },
    )
    payload = json.dumps(to_devalue(root), ensure_ascii=False)
    payload = payload.replace("<", chr(92) + "u003C")
    return (
        "<!DOCTYPE html><html><head><title>Metacritic</title></head><body>"
        '<div id="__nuxt"></div><script data-nuxt-data="nuxt-app" data-ssr="true" '
        f'id="__NUXT_DATA__" type="application/json">{payload}</script></body></html>'
    )


def page(name: str) -> str:
    """A fixture state rendered as a Metacritic page."""
    return nuxt_page(fixture_json(name))


class FakeClient:
    """Stands in for ``scrapeunblocker.Client``: answers ``get_page_source`` from
    ``respond(url)`` (a body, or an exception to raise) and records every call."""

    def __init__(self, respond: Callable[[str], Any]):
        self.respond = respond
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get_page_source(self, url: str, **kwargs: Any) -> str:
        self.calls.append((url, kwargs))
        result = self.respond(url)
        if isinstance(result, BaseException):
            raise result
        return result

    @property
    def urls(self) -> list[str]:
        return [url for url, _ in self.calls]


def sequence(*answers: Any) -> Callable[[str], Any]:
    """A ``respond`` that returns the answers in order (the last one repeats)."""
    queue = list(answers)

    def respond(url: str) -> Any:
        return queue.pop(0) if len(queue) > 1 else queue[0]

    return respond


def by_url(routes: dict[str, Any], default: Any = None) -> Callable[[str], Any]:
    """A ``respond`` that picks the answer whose key is a substring of the URL."""

    def respond(url: str) -> Any:
        for key, answer in routes.items():
            if key in url:
                return answer
        if default is None:
            raise AssertionError(f"unexpected URL {url}")
        return default

    return respond


def feed(total: int, items: list[dict[str, Any]]) -> str:
    """A JSON feed response with ``items``."""
    return json.dumps({"data": {"totalResults": total, "items": items}})


@pytest.fixture
def make_mc() -> Callable[..., tuple[Metacritic, FakeClient]]:
    def make(respond: Callable[[str], Any], **kwargs: Any) -> tuple[Metacritic, FakeClient]:
        client = FakeClient(respond)
        kwargs.setdefault("sleep", lambda seconds: None)
        return Metacritic(client=client, **kwargs), client

    return make
