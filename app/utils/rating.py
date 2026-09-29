"""
Star rating calculation and utilities for resume analysis scores.
"""
from typing import Tuple


def compute_star_rating(score: float | int | None) -> Tuple[float, int, bool, int]:
    """
    Convert a numeric score (0 - 100) into a 5-star rating with half-star precision.

    Logic:
        stars = round((score / 100) * 5, 1)

    Returns:
        star_rating (float): e.g. 4.2
        full_stars (int): count of full stars (0 to 5)
        half_star (bool): whether there is a half star (True/False)
        empty_stars (int): count of empty stars (0 to 5)

    Guarantees:
        full_stars + (1 if half_star else 0) + empty_stars == 5
    """
    if score is None:
        score = 0.0
    try:
        score_val = float(score)
    except (ValueError, TypeError):
        score_val = 0.0

    score_val = max(0.0, min(100.0, score_val))
    star_rating = round((score_val / 100.0) * 5.0, 1)

    floor = int(star_rating)
    decimal = round(star_rating - floor, 1)

    if decimal >= 0.8:
        full_stars = min(5, floor + 1)
        half_star = False
    elif decimal >= 0.3:
        full_stars = min(4, floor)
        half_star = True
    else:
        full_stars = min(5, floor)
        half_star = False

    empty_stars = max(0, 5 - full_stars - (1 if half_star else 0))
    return star_rating, full_stars, half_star, empty_stars
