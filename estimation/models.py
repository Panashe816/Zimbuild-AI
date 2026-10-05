from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ================================================================
# SCALE
# ================================================================

@dataclass
class ScaleInformation:
    """
    Represents the image scale established by the scale service.

    scale_label:
        Human-readable architectural scale such as 1:100.

    pixels_per_metre:
        Actual calibration of the processed digital image.

    status:
        calibrated, detected, or required.

    method:
        Method used to establish the scale.
    """

    status: str = "required"

    method: Optional[str] = None

    scale_label: Optional[str] = None

    scale_ratio: Optional[float] = None

    pixels_per_metre: Optional[float] = None

    metres_per_pixel: Optional[float] = None

    confidence: float = 0.0

    message: str = ""


# ================================================================
# WALL MEASUREMENT
# ================================================================

@dataclass
class WallMeasurement:
    """
    Represents a wall measurement produced by the Phase 8
    wall detection and measurement pipeline.
    """

    wall_id: str

    length_m: float

    orientation: str = "unknown"

    width_m: Optional[float] = None


# ================================================================
# OPENINGS
# ================================================================

@dataclass
class Opening:
    """
    Represents an opening such as a door or window in a wall.
    """

    opening_id: str

    opening_type: str

    width_m: float

    height_m: float

    wall_id: Optional[str] = None

    @property
    def area_m2(self) -> float:
        """Calculate the opening area in square metres."""
        return self.width_m * self.height_m


# ================================================================
# ROOM
# ================================================================

@dataclass
class Room:
    """
    Represents a detected room or enclosed room candidate.

    room_type is optional because the detector may identify an
    enclosed room without being able to reliably classify it as
    bedroom, kitchen, bathroom, living room, etc.
    """

    room_id: str

    room_type: Optional[str] = None

    area_m2: Optional[float] = None

    confidence: float = 0.0

    x1: Optional[float] = None
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None

    metadata: Dict[str, object] = field(
        default_factory=dict
    )


# ================================================================
# DOOR
# ================================================================

@dataclass
class Door:
    """
    Represents a detected door opening.
    """

    door_id: str

    width_m: Optional[float] = None

    height_m: Optional[float] = None

    confidence: float = 0.0

    wall_id: Optional[str] = None

    metadata: Dict[str, object] = field(
        default_factory=dict
    )

    @property
    def area_m2(self) -> Optional[float]:
        """Return door area when both dimensions are available."""
        if self.width_m is None or self.height_m is None:
            return None

        return self.width_m * self.height_m


# ================================================================
# WINDOW
# ================================================================

@dataclass
class Window:
    """
    Represents a detected window opening.
    """

    window_id: str

    width_m: Optional[float] = None

    height_m: Optional[float] = None

    confidence: float = 0.0

    wall_id: Optional[str] = None

    metadata: Dict[str, object] = field(
        default_factory=dict
    )

    @property
    def area_m2(self) -> Optional[float]:
        """Return window area when both dimensions are available."""
        if self.width_m is None or self.height_m is None:
            return None

        return self.width_m * self.height_m


# ================================================================
# ROOF
# ================================================================

@dataclass
class RoofInformation:
    """
    Represents roof information detected from the architectural plan.

    Roof quantities are only generated when sufficient roof
    information is available.
    """

    roof_present: bool = False

    roof_type: Optional[str] = None

    roof_area_m2: Optional[float] = None

    confidence: float = 0.0

    metadata: Dict[str, object] = field(
        default_factory=dict
    )


# ================================================================
# CONSTRUCTION PARAMETERS
# ================================================================

@dataclass
class ConstructionParameters:
    """
    User-confirmed construction parameters required for
    quantity estimation.

    Wall parameters are used for masonry calculations.

    Additional roof and construction-material parameters are
    available for deterministic estimation of roofing, timber,
    water and quarry stone requirements.

    Scale is deliberately NOT a manual construction parameter.
    Scale is supplied by the automatic scale service.
    """

    # ============================================================
    # WALL PARAMETERS
    # ============================================================

    wall_height_m: float

    wall_thickness_m: float

    # ============================================================
    # OPTIONAL FINISHING PARAMETERS
    # ============================================================

    plaster_thickness_m: Optional[float] = None

    floor_screed_thickness_m: Optional[float] = None

    # ============================================================
    # ROOF PARAMETERS
    # ============================================================

    roof_area_m2: Optional[float] = None

    roof_sheet_coverage_m2: Optional[float] = None

    # ============================================================
    # TIMBER PARAMETERS
    # ============================================================

    roof_timber_length_m: Optional[float] = None

    timber_spacing_m: Optional[float] = None

    # ============================================================
    # OTHER CONSTRUCTION MATERIAL PARAMETERS
    # ============================================================

    water_allowance_litres: Optional[float] = None

    quarry_stone_volume_m3: Optional[float] = None

    # ============================================================
    # GENERAL WASTAGE
    # ============================================================

    wastage_percentage: float = 5.0

    def __post_init__(self) -> None:

        if self.wall_height_m <= 0:
            raise ValueError(
                "Wall height must be greater than zero."
            )

        if self.wall_thickness_m <= 0:
            raise ValueError(
                "Wall thickness must be greater than zero."
            )

        if self.plaster_thickness_m is not None:

            if self.plaster_thickness_m < 0:
                raise ValueError(
                    "Plaster thickness cannot be negative."
                )

        if self.floor_screed_thickness_m is not None:

            if self.floor_screed_thickness_m < 0:
                raise ValueError(
                    "Floor screed thickness cannot be negative."
                )

        if self.roof_area_m2 is not None:

            if self.roof_area_m2 <= 0:
                raise ValueError(
                    "Roof area must be greater than zero."
                )

        if self.roof_sheet_coverage_m2 is not None:

            if self.roof_sheet_coverage_m2 <= 0:
                raise ValueError(
                    "Roof sheet coverage must be greater than zero."
                )

        if self.roof_timber_length_m is not None:

            if self.roof_timber_length_m <= 0:
                raise ValueError(
                    "Roof timber length must be greater than zero."
                )

        if self.timber_spacing_m is not None:

            if self.timber_spacing_m <= 0:
                raise ValueError(
                    "Timber spacing must be greater than zero."
                )

        if self.water_allowance_litres is not None:

            if self.water_allowance_litres <= 0:
                raise ValueError(
                    "Water allowance must be greater than zero."
                )

        if self.quarry_stone_volume_m3 is not None:

            if self.quarry_stone_volume_m3 <= 0:
                raise ValueError(
                    "Quarry stone volume must be greater than zero."
                )

        if self.wastage_percentage < 0:

            raise ValueError(
                "Wastage percentage cannot be negative."
            )


# ================================================================
# WALL QUANTITY
# ================================================================

@dataclass
class WallQuantity:
    """
    Calculated construction quantities for a wall.
    """

    wall_id: str

    length_m: float

    height_m: float

    thickness_m: float

    gross_area_m2: float

    opening_area_m2: float

    net_area_m2: float

    volume_m3: float

    openings: List[Opening] = field(
        default_factory=list
    )


# ================================================================
# BUILDING QUANTITY SUMMARY
# ================================================================

@dataclass
class BuildingQuantitySummary:
    """
    Overall calculated building quantities.

    This remains compatible with the existing Phase 9 quantity
    calculation while providing additional architectural
    information for later construction-stage calculations.
    """

    wall_count: int = 0

    total_wall_length_m: float = 0.0

    total_gross_wall_area_m2: float = 0.0

    total_opening_area_m2: float = 0.0

    total_net_wall_area_m2: float = 0.0

    total_wall_volume_m3: float = 0.0

    door_count: int = 0

    window_count: int = 0

    total_door_area_m2: float = 0.0

    total_window_area_m2: float = 0.0

    room_count: int = 0

    total_floor_area_m2: float = 0.0

    roof_present: bool = False

    roof_area_m2: Optional[float] = None


# ================================================================
# CONSTRUCTION STAGE
# ================================================================

@dataclass
class ConstructionStage:
    """
    Represents one construction stage.

    The stage names are fixed so the pricing and BoQ layers can
    consistently identify them.
    """

    stage_id: str

    stage_name: str

    description: str = ""

    sequence: int = 0


# ================================================================
# STAGE QUANTITY
# ================================================================

@dataclass
class StageQuantity:
    """
    Represents a quantity assigned to a particular construction
    stage.

    Example:

        stage_id = "footing"
        material_id = "cement_50kg"
        quantity = 20
        unit = "bag"
    """

    stage_id: str

    stage_name: str

    material_id: str

    material_name: str

    quantity: float

    unit: str

    source: str = ""

    metadata: Dict[str, object] = field(
        default_factory=dict
    )


# ================================================================
# FULL DETECTION RESULT
# ================================================================

@dataclass
class ArchitecturalPlan:
    """
    Unified architectural plan information passed between the
    detection and estimation layers.
    """

    scale: Optional[ScaleInformation] = None

    walls: List[WallMeasurement] = field(
        default_factory=list
    )

    rooms: List[Room] = field(
        default_factory=list
    )

    doors: List[Door] = field(
        default_factory=list
    )

    windows: List[Window] = field(
        default_factory=list
    )

    roof: Optional[RoofInformation] = None

    metadata: Dict[str, object] = field(
        default_factory=dict
    )