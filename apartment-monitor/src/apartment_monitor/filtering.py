from __future__ import annotations

from .models import ApartmentListing, SearchCriterion


def listing_matches(
    listing: ApartmentListing,
    criteria: list[SearchCriterion],
    neighborhoods: list[str],
) -> bool:
    return matching_criterion(listing, criteria, neighborhoods) is not None


def matching_criterion(
    listing: ApartmentListing,
    criteria: list[SearchCriterion],
    neighborhoods: list[str],
) -> SearchCriterion | None:
    if listing.price is None or listing.bedrooms is None or listing.bathrooms is None:
        return None
    if neighborhoods and not _matches_neighborhood(listing, neighborhoods):
        return None
    for criterion in criteria:
        if (
            listing.bedrooms == criterion.bedrooms
            and listing.bathrooms >= criterion.min_bathrooms
            and listing.price <= criterion.max_price
        ):
            return criterion
    return None


def _matches_neighborhood(listing: ApartmentListing, neighborhoods: list[str]) -> bool:
    haystack = listing.text_for_matching()
    normalized = [_normalize_area(area) for area in neighborhoods]
    return any(area and area in haystack for area in normalized)


def _normalize_area(area: str) -> str:
    return " ".join(area.casefold().split())
