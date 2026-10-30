"""Export a title's critic and user reviews to two CSV files.

python examples/reviews_to_csv.py                      # Elden Ring
python examples/reviews_to_csv.py movie/oppenheimer 200
python examples/reviews_to_csv.py tv/the-bear/season-3
"""

from __future__ import annotations

import sys

from metacritic_scraper import Metacritic, parse_ref
from metacritic_scraper.export import write

ref = sys.argv[1] if len(sys.argv) > 1 else "elden-ring"
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100

mc = Metacritic()  # reads SCRAPEUNBLOCKER_KEY
title = parse_ref(ref)
name = f"{title.slug}_{title.season}" if title.season else title.slug

for kind in ("critic", "user"):
    result = mc.reviews(ref, kind=kind, sort="newest", limit=limit)
    path = f"{name}_{kind}_reviews.csv"
    write(result.reviews, "csv", path)
    scores = [r.score for r in result.reviews if r.score is not None]
    average = sum(scores) / len(scores) if scores else float("nan")
    print(f"{path}: {len(result.reviews)} of {result.total} {kind} reviews, average {average:.1f}")

print(f"{mc.requests} API requests")
