from .models import TransportRate, TransportRequirement
from .price_database import get_transport_rate


def calculate_transport_cost(
    requirement: TransportRequirement,
    rate: TransportRate | None = None,
) -> float:

    if rate is None:
        raise ValueError(
            "A location-specific transport rate must be provided."
        )

    return (
        requirement.load_count
        * requirement.distance_km
        * rate.price_per_load_per_km
    )


def calculate_transport_cost_from_loads(
    load_count: int,
    distance_km: float,
    location_profile_id: str = "city_town",
) -> float:

    requirement = TransportRequirement(
        load_count=load_count,
        distance_km=distance_km,
    )

    rate = get_transport_rate(location_profile_id)

    return calculate_transport_cost(
        requirement=requirement,
        rate=rate,
    )