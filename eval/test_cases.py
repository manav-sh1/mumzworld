"""Test case definitions for the gift finder evaluation suite."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TestCase:
    """A single evaluation test case."""

    id: str
    description: str
    query: str
    age_months: int | None = None
    budget_aed: float | None = None
    expects_refusal: bool = False
    expects_clarification: bool = False
    min_recommendations: int = 0
    max_recommendations: int = 5


TEST_CASES: list[TestCase] = [
    TestCase(
        id="TC01",
        description="Standard happy path (EN)",
        query="gift for a friend with a 6-month-old, under 200 AED",
        age_months=6,
        budget_aed=200,
        min_recommendations=1,
    ),
    TestCase(
        id="TC02",
        description="Standard happy path (AR)",
        query="هدية لصديقتي عندها طفل عمره 6 أشهر، الميزانية 200 درهم",
        age_months=6,
        budget_aed=200,
        min_recommendations=1,
    ),
    TestCase(
        id="TC03",
        description="No budget specified",
        query="thoughtful gift for a newborn baby girl",
        age_months=0,
        expects_clarification=True,
    ),
    TestCase(
        id="TC04",
        description="Budget too low",
        query="gift for a 1-year-old, budget is 10 AED",
        age_months=12,
        budget_aed=10,
        expects_refusal=True,
        max_recommendations=0,
    ),
    TestCase(
        id="TC05",
        description="No matching product — 5-year-old, low budget",
        query="gift for a 5-year-old, budget 50 AED",
        age_months=60,
        budget_aed=50,
        expects_refusal=True,
        max_recommendations=0,
    ),
    TestCase(
        id="TC06",
        description="Out of scope — adult gift",
        query="gift for a pregnant mom, something for herself",
        expects_refusal=True,
        max_recommendations=0,
    ),
    TestCase(
        id="TC07",
        description="Adversarial vague input",
        query="something nice for a baby",
        expects_clarification=True,
    ),
    TestCase(
        id="TC08",
        description="High budget, multiple options",
        query="gift for a 6-month-old, budget 1000 AED",
        age_months=6,
        budget_aed=1000,
        min_recommendations=3,
    ),
    TestCase(
        id="TC09",
        description="Specific interest — music + educational",
        query="educational gift for a 12-month-old who loves music",
        age_months=12,
        min_recommendations=1,
    ),
    TestCase(
        id="TC10",
        description="Bilingual stress test",
        query="gift for my friend's baby, 9 months old, budget 150 AED, هدية مميزة",
        age_months=9,
        budget_aed=150,
        min_recommendations=1,
    ),
    TestCase(
        id="TC11",
        description="Edge case age — 3-year-old toddler",
        query="gift for a 3-year-old toddler, budget 300 AED",
        age_months=36,
        budget_aed=300,
        min_recommendations=1,
    ),
    TestCase(
        id="TC12",
        description="Refusal — non-gift general knowledge query",
        query="what is the best stroller on the market globally",
        expects_refusal=True,
        max_recommendations=0,
    ),
]
