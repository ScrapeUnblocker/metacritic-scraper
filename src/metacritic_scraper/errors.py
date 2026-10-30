"""Errors raised by the scraper."""

from __future__ import annotations


class MetacriticError(Exception):
    """Base class for scraper errors."""


class NotFoundError(MetacriticError):
    """Metacritic answered 404: an unknown title, season or review platform."""


class ParseError(MetacriticError):
    """A response did not contain the expected Metacritic data."""


class FilterError(MetacriticError, ValueError):
    """A filter value Metacritic does not accept (the message lists the valid ones)."""
