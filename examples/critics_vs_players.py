"""Where critics and players disagree: the biggest Metascore vs user score gaps.

Reads the top-rated games of a year (three browse pages, 72 games) and prints the
games critics liked much more than players, and the other way round.

    python examples/critics_vs_players.py          # last year
    python examples/critics_vs_players.py 2023
"""

from __future__ import annotations

import datetime
import sys

from metacritic_scraper import BrowseFilters, Metacritic

year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today().year - 1

mc = Metacritic()  # reads SCRAPEUNBLOCKER_KEY
result = mc.browse("game", BrowseFilters(year=year), pages=3)
games = [g for g in result.titles if g.score_gap is not None and (g.critic_review_count or 0) >= 15]
games.sort(key=lambda g: g.score_gap)
critics_favourites = [g for g in reversed(games) if g.score_gap > 0][:5]
players_favourites = [g for g in games if g.score_gap < 0][:5]


def show(title: str, rows: list) -> None:
    print(title)
    for g in rows:
        print(
            f"  {g.score_gap:+6.1f}  Metascore {g.metascore:>3}  users {g.user_score:4.1f}  "
            f"{g.title} ({', '.join(g.platforms)})"
        )
    if not rows:
        print("  (none)")
    print()


print(f"{len(games)} of the top {len(result.titles)} games of {year} have both scores\n")
show("Critics liked more than players:", critics_favourites)
show("Players liked more than critics:", players_favourites)
