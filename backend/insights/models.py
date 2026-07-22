from django.db import models  # noqa: F401

# TravelInsight, DestinationStat, CategorySpend, MonthlyTrend, and TravelAnalytics
# were removed 2026-07-22 — they had zero rows in the database, no population
# pipeline anywhere in the codebase, and no frontend caller. The rest of this
# app (dashboard_summary, travel_spend_analytics, etc. in views.py) is live,
# used, read-only aggregation against other apps' models and is unaffected.
# See docs/APP_WIDE_GAPS_FIX_ROADMAP.md Fix 2.
