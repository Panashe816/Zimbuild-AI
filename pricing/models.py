from dataclasses import dataclass
from typing import Optional


# ============================================================
# PRICE RECORD
# ============================================================

@dataclass(frozen=True)
class PriceRecord:
    material_id: str
    material_name: str
    category: str
    price: float
    unit: str
    currency: str = "USD"
    location: str = "Zimbabwe"
    supplier: Optional[str] = None
    source: Optional[str] = None
    effective_date: Optional[str] = None
    active: bool = True

    def __post_init__(self):
        if not self.material_id.strip():
            raise ValueError("Material ID cannot be empty.")

        if not self.material_name.strip():
            raise ValueError("Material name cannot be empty.")

        if not self.category.strip():
            raise ValueError("Material category cannot be empty.")

        if self.price < 0:
            raise ValueError("Price cannot be negative.")

        if not self.unit.strip():
            raise ValueError("Price unit cannot be empty.")

        if not self.currency.strip():
            raise ValueError("Currency cannot be empty.")


# ============================================================
# TRANSPORT RATE
# ============================================================

@dataclass(frozen=True)
class TransportRate:
    """
    Location-specific transport rate.

    Transport cost is calculated as:

        load_count × distance_km × price_per_load_per_km
    """

    price_per_load_per_km: float
    currency: str = "USD"

    def __post_init__(self):
        if self.price_per_load_per_km < 0:
            raise ValueError(
                "Transport price per load per kilometre cannot be negative."
            )

        if not self.currency.strip():
            raise ValueError("Currency cannot be empty.")


# ============================================================
# TRANSPORT REQUIREMENT
# ============================================================

@dataclass(frozen=True)
class TransportRequirement:
    load_count: int
    distance_km: float

    def __post_init__(self):
        if self.load_count < 0:
            raise ValueError("Load count cannot be negative.")

        if self.distance_km < 0:
            raise ValueError("Distance cannot be negative.")


# ============================================================
# MATERIAL COST
# ============================================================

@dataclass(frozen=True)
class MaterialCost:
    material_name: str
    quantity: float
    unit: str
    unit_price: float
    material_cost: float
    currency: str = "USD"
    transport_cost: float = 0.0

    @property
    def delivered_cost(self) -> float:
        return self.material_cost + self.transport_cost


# ============================================================
# UNPRICED MATERIAL
# ============================================================

@dataclass(frozen=True)
class UnpricedMaterial:
    material_name: str
    quantity: float
    unit: str
    reason: str = "Price unavailable"

    def __post_init__(self):
        if not self.material_name.strip():
            raise ValueError("Material name cannot be empty.")

        if self.quantity < 0:
            raise ValueError("Material quantity cannot be negative.")

        if not self.unit.strip():
            raise ValueError("Material unit cannot be empty.")

        if not self.reason.strip():
            raise ValueError("Reason cannot be empty.")