"""The best-reviewed games of a year on one platform, as JSON.

python examples/best_games_on_platform.py            # PS5, this year
python examples/best_games_on_platform.py switch 2024
"""

from __future__ import annotations

import datetime
import json
import sys

from metacritic_scraper import BrowseFilters, Metacritic

platform = sys.argv[1] if len(sys.argv) > 1 else "ps5"
year = int(sys.argv[2]) if len(sys.argv) > 2 else datetime.date.today().year

mc = Metacritic()  # reads SCRAPEUNBLOCKER_KEY
result = mc.browse("game", BrowseFilters(platforms=[platform], year=year), limit=10)

print(
    json.dumps(
        {
            "platform": platform,
            "year": year,
            "scored_games": result.total,
            "top10": [
                {
                    "rank": game.rank,
                    "title": game.title,
                    "metascore": game.metascore,
                    "critic_reviews": game.critic_review_count,
                    "user_score": game.user_score,
                    "genres": game.genres,
                    "released": game.release_date,
                    "url": game.url,
                }
                for game in result.titles
            ],
        },
        indent=2,
        ensure_ascii=False,
    )
)
