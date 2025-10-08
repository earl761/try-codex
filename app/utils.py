"""Utility helpers for itinerary formatting."""
from __future__ import annotations

from typing import Iterable

from jinja2 import Environment, PackageLoader, select_autoescape

from . import models


def render_itinerary(itinerary: models.Itinerary) -> str:
    """Render an itinerary into a printable text/HTML hybrid document."""
    env = Environment(
        loader=PackageLoader("app", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
        enable_async=False,
    )
    template = env.get_template("itinerary.html")
    return template.render(itinerary=itinerary)


def compute_outstanding_balance(payments: Iterable[models.Payment], amount_due: float) -> float:
    total_paid = sum(float(payment.amount) for payment in payments)
    return round(amount_due - total_paid, 2)
