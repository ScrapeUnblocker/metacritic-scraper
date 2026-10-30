from __future__ import annotations

import json
import math

import pytest
from conftest import Wrapped, nuxt_page, to_devalue

from metacritic_scraper.nuxt import NuxtDataError, decode, extract, find_payload


def test_decodes_references_wrappers_and_specials():
    payload = [
        ["ShallowReactive", 1],
        {"title": 2, "tags": 3, "again": 2, "missing": -1, "nan": -3, "when": 6, "set": 7},
        "Elden Ring",
        [2, 4, 5],
        96,
        None,
        ["Date", "2022-02-25T00:00:00.000Z"],
        ["Set", 4, 2],
    ]
    data = decode(json.dumps(payload))
    assert data["title"] == "Elden Ring"
    assert data["tags"] == ["Elden Ring", 96, None]
    assert data["again"] == "Elden Ring"
    assert data["missing"] is None
    assert math.isnan(data["nan"])
    assert data["when"] == "2022-02-25T00:00:00.000Z"
    assert data["set"] == [96, "Elden Ring"]


def test_custom_reducers_unwrap_their_single_value():
    assert decode([["MetacriticThing", 1], {"a": 2}, 1]) == {"a": 1}


def test_round_trips_the_test_encoder():
    value = {"data": {"items": [{"id": 1, "name": "x"}, {"id": 2, "name": None}]}, "ok": True}
    assert decode(to_devalue(value)) == value
    wrapped = decode(to_devalue(Wrapped("Reactive", {"a": [1, 2]})))
    assert wrapped == {"a": [1, 2]}


@pytest.mark.parametrize(
    "payload",
    ["not json", "{}", "[]", json.dumps([{"a": 5}]), json.dumps([{"a": "x"}])],
)
def test_bad_payloads_raise(payload):
    with pytest.raises(NuxtDataError):
        decode(payload)


def test_extract_finds_the_script():
    html = nuxt_page({"path": "/game/x/", "data": {"k": {"v": 1}}})
    assert find_payload(html)
    state = extract(html)
    assert state["path"] == "/game/x/"
    assert state["data"] == {"k": {"v": 1}}


def test_extract_without_payload_raises():
    with pytest.raises(NuxtDataError):
        extract("<html><body>Just a moment...</body></html>")
