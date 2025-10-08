"""API router package for the Tour Planner service."""
from fastapi import APIRouter

from .routes import clients, finance, itineraries, leads, reports, tour_packages

router = APIRouter()
router.include_router(clients.router)
router.include_router(leads.router)
router.include_router(tour_packages.router)
router.include_router(itineraries.router)
router.include_router(finance.router)
router.include_router(reports.router)

__all__ = ["router"]
