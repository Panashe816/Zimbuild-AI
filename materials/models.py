from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ================================================================
# CONSTRUCTION PARAMETERS
# ================================================================

@dataclass
class MasonryParameters:
    """
    Construction parameters used by the ZimBuild AI
    quantity and material calculation layers.

    These are construction specifications/assumptions.
    They are NOT final material quantities.

    Values detected from an architectural plan should take
    precedence over defaults where available.

    Any parameter that cannot be reliably obtained from the
    uploaded plan should be explicitly supplied or confirmed
    by the user rather than silently invented.
    """

    # ------------------------------------------------------------
    # Brick dimensions
    # ------------------------------------------------------------

    brick_length_m: float = 0.230
    brick_height_m: float = 0.076
    brick_thickness_m: float = 0.110

    # ------------------------------------------------------------
    # Wall parameters
    # ------------------------------------------------------------

    wall_thickness_m: float = 0.200

    wall_height_m: float = 2.700

    # ------------------------------------------------------------
    # Mortar
    # ------------------------------------------------------------

    mortar_joint_m: float = 0.010

    # ------------------------------------------------------------
    # Wastage
    # ------------------------------------------------------------

    wastage_percentage: float = 5.0

    # ------------------------------------------------------------
    # FOUNDATION PARAMETERS
    # ------------------------------------------------------------

    # These are construction dimensions, not calculated quantities.
    #
    # They should eventually come from:
    #   1. architectural/structural information, or
    #   2. explicit user confirmation.
    #
    # None means that the value has not yet been supplied.

    foundation_width_m: Optional[float] = None

    foundation_depth_m: Optional[float] = None

    foundation_concrete_thickness_m: Optional[float] = None

    # ------------------------------------------------------------
    # FLOOR / SLAB PARAMETERS
    # ------------------------------------------------------------

    slab_thickness_m: Optional[float] = None

    hardcore_depth_m: Optional[float] = None

    blinding_thickness_m: Optional[float] = None

    # ------------------------------------------------------------
    # DAMP-PROOFING PARAMETERS
    # ------------------------------------------------------------

    # DPM coverage will normally be calculated from floor area.
    # This optional allowance can be used where an explicit
    # additional coverage factor is required.

    dpm_wastage_percentage: Optional[float] = None

    # ------------------------------------------------------------
    # GENERAL CONSTRUCTION MATERIAL PARAMETERS
    # ------------------------------------------------------------

    water_allowance_litres: Optional[float] = None

    quarry_stone_volume_m3: Optional[float] = None

    hardcore_volume_m3: Optional[float] = None

    # ------------------------------------------------------------
    # REINFORCEMENT PARAMETERS
    # ------------------------------------------------------------

    reinforcement_steel_kg: Optional[float] = None

    reinforcement_mesh_m2: Optional[float] = None

    binding_wire_kg: Optional[float] = None

    # ------------------------------------------------------------
    # OPENING / LINTEL PARAMETERS
    # ------------------------------------------------------------

    lintel_length_allowance_m: Optional[float] = None

    # ------------------------------------------------------------
    # ROOFING
    # ------------------------------------------------------------
    #
    # Roofing is intentionally retained in the model for backward
    # compatibility with the existing project.
    #
    # Roofing will NOT be used by the new building-material
    # workflow at this stage.

    roof_area_m2: Optional[float] = None

    roof_sheet_coverage_m2: Optional[float] = None

    roof_timber_length_m: Optional[float] = None

    timber_spacing_m: Optional[float] = None

    def __post_init__(self) -> None:
        """
        Validate construction parameters.
        """

        # --------------------------------------------------------
        # Brick validation
        # --------------------------------------------------------

        if self.brick_length_m <= 0:
            raise ValueError(
                "Brick length must be greater than zero."
            )

        if self.brick_height_m <= 0:
            raise ValueError(
                "Brick height must be greater than zero."
            )

        if self.brick_thickness_m <= 0:
            raise ValueError(
                "Brick thickness must be greater than zero."
            )

        # --------------------------------------------------------
        # Wall validation
        # --------------------------------------------------------

        if self.wall_thickness_m <= 0:
            raise ValueError(
                "Wall thickness must be greater than zero."
            )

        if self.wall_height_m <= 0:
            raise ValueError(
                "Wall height must be greater than zero."
            )

        # --------------------------------------------------------
        # Mortar validation
        # --------------------------------------------------------

        if self.mortar_joint_m < 0:
            raise ValueError(
                "Mortar joint cannot be negative."
            )

        # --------------------------------------------------------
        # Wastage validation
        # --------------------------------------------------------

        if self.wastage_percentage < 0:
            raise ValueError(
                "Wastage percentage cannot be negative."
            )

        if self.dpm_wastage_percentage is not None:
            if self.dpm_wastage_percentage < 0:
                raise ValueError(
                    "DPM wastage percentage cannot be negative."
                )

        # --------------------------------------------------------
        # Foundation validation
        # --------------------------------------------------------

        if self.foundation_width_m is not None:
            if self.foundation_width_m <= 0:
                raise ValueError(
                    "Foundation width must be greater than zero."
                )

        if self.foundation_depth_m is not None:
            if self.foundation_depth_m <= 0:
                raise ValueError(
                    "Foundation depth must be greater than zero."
                )

        if self.foundation_concrete_thickness_m is not None:
            if self.foundation_concrete_thickness_m <= 0:
                raise ValueError(
                    "Foundation concrete thickness must be greater than zero."
                )

        # --------------------------------------------------------
        # Slab validation
        # --------------------------------------------------------

        if self.slab_thickness_m is not None:
            if self.slab_thickness_m <= 0:
                raise ValueError(
                    "Slab thickness must be greater than zero."
                )

        if self.hardcore_depth_m is not None:
            if self.hardcore_depth_m <= 0:
                raise ValueError(
                    "Hardcore depth must be greater than zero."
                )

        if self.blinding_thickness_m is not None:
            if self.blinding_thickness_m <= 0:
                raise ValueError(
                    "Blinding thickness must be greater than zero."
                )

        # --------------------------------------------------------
        # General material validation
        # --------------------------------------------------------

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

        if self.hardcore_volume_m3 is not None:
            if self.hardcore_volume_m3 <= 0:
                raise ValueError(
                    "Hardcore volume must be greater than zero."
                )

        # --------------------------------------------------------
        # Reinforcement validation
        # --------------------------------------------------------

        if self.reinforcement_steel_kg is not None:
            if self.reinforcement_steel_kg <= 0:
                raise ValueError(
                    "Reinforcement steel quantity must be greater than zero."
                )

        if self.reinforcement_mesh_m2 is not None:
            if self.reinforcement_mesh_m2 <= 0:
                raise ValueError(
                    "Reinforcement mesh quantity must be greater than zero."
                )

        if self.binding_wire_kg is not None:
            if self.binding_wire_kg <= 0:
                raise ValueError(
                    "Binding wire quantity must be greater than zero."
                )

        # --------------------------------------------------------
        # Lintel validation
        # --------------------------------------------------------

        if self.lintel_length_allowance_m is not None:
            if self.lintel_length_allowance_m <= 0:
                raise ValueError(
                    "Lintel length allowance must be greater than zero."
                )

        # --------------------------------------------------------
        # Roofing validation
        # --------------------------------------------------------

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


# ================================================================
# MATERIAL QUANTITY
# ================================================================

@dataclass
class MaterialQuantity:
    """
    Represents a calculated quantity of one construction material.

    This is the main material-calculation object used by the
    existing material engine.

    Mortar is deliberately not represented as a user-facing
    material. Mortar calculations are performed internally to
    derive cement and building-sand requirements.
    """

    material_name: str
    quantity: float
    unit: str

    # Optional identifiers and metadata preserve compatibility
    # with the wider estimation pipeline.

    material_id: Optional[str] = None

    category: Optional[str] = None

    source: Optional[str] = None

    metadata: Dict[str, object] = field(
        default_factory=dict
    )


# ================================================================
# STAGE MATERIAL QUANTITY
# ================================================================

@dataclass
class StageMaterialQuantity:
    """
    Represents a construction material allocated to a specific
    construction stage.
    """

    stage_id: str

    stage_name: str

    material_id: str

    material_name: str

    quantity: float

    unit: str

    category: str = "Other"

    source: str = ""

    metadata: Dict[str, object] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """
        Validate stage material quantity.
        """

        if not self.stage_id:
            raise ValueError(
                "Stage ID cannot be empty."
            )

        if not self.stage_name:
            raise ValueError(
                "Stage name cannot be empty."
            )

        if not self.material_id:
            raise ValueError(
                "Material ID cannot be empty."
            )

        if not self.material_name:
            raise ValueError(
                "Material name cannot be empty."
            )

        if self.quantity < 0:
            raise ValueError(
                "Material quantity cannot be negative."
            )

        if not self.unit:
            raise ValueError(
                "Material unit cannot be empty."
            )


# ================================================================
# STAGE MATERIAL SUMMARY
# ================================================================

@dataclass
class StageMaterialSummary:
    """
    Collection of calculated material quantities grouped by
    construction stage.
    """

    quantities: List[StageMaterialQuantity] = field(
        default_factory=list
    )

    def add(
        self,
        quantity: StageMaterialQuantity,
    ) -> None:
        """
        Add a stage material quantity.
        """

        self.quantities.append(
            quantity
        )

    def get_stage(
        self,
        stage_id: str,
    ) -> List[StageMaterialQuantity]:
        """
        Return all materials belonging to a specific stage.
        """

        return [
            item
            for item in self.quantities
            if item.stage_id == stage_id
        ]

    def get_material(
        self,
        material_id: str,
    ) -> List[StageMaterialQuantity]:
        """
        Return all occurrences of a material across stages.
        """

        return [
            item
            for item in self.quantities
            if item.material_id == material_id
        ]

    @property
    def total_quantity_records(self) -> int:
        """
        Return the number of material quantity records.
        """

        return len(self.quantities)


# ================================================================
# STANDARD MATERIAL IDENTIFIERS
# ================================================================

STANDARD_BRICK = "standard_brick"

CEMENT = "cement_50kg"

BUILDING_SAND = "building_sand"

QUARRY_STONE = "quarry_stone"

QUARRY_DUST = "quarry_dust"

CONSTRUCTION_WATER = "construction_water"

REINFORCEMENT_STEEL = "reinforcement_steel"

REINFORCEMENT_MESH = "reinforcement_mesh"

BINDING_WIRE = "binding_wire"

HARDCORE = "hardcore"

DPM = "dpm"

DPC = "dpc"

LINTEL = "lintel"

FORMWORK_TIMBER = "formwork_timber"

NAILS = "nails"

FIBRE_CEMENT_SHEET = "fibre_cement_sheet"

TIMBER_POLE = "timber_pole_6m"

ROOFING_TIMBER = "roofing_timber"

RIDGE_CAP = "ridge_cap"

FASCIA = "fascia"


# ================================================================
# STANDARD STAGE IDENTIFIERS
# ================================================================

STAGE_FOOTING = "footing"

STAGE_SLAB = "slab"

STAGE_WINDOW_LEVEL = "window_level"

STAGE_FINAL_WALL = "final_wall"

STAGE_ROOFING = "roofing"


# ================================================================
# TESTS
# ================================================================

def _run_tests() -> None:
    """
    Run material-model tests.
    """

    print("=" * 70)
    print("ZIMBUILD AI - MATERIAL MODELS TESTS")
    print("=" * 70)

    # ------------------------------------------------------------
    # Masonry parameters
    # ------------------------------------------------------------

    masonry = MasonryParameters()

    assert masonry.brick_length_m == 0.230
    assert masonry.brick_height_m == 0.076
    assert masonry.brick_thickness_m == 0.110

    assert masonry.wall_thickness_m == 0.200
    assert masonry.wall_height_m == 2.700

    assert masonry.mortar_joint_m == 0.010
    assert masonry.wastage_percentage == 5.0

    print("Basic masonry parameters: PASS")

    # ------------------------------------------------------------
    # Construction parameters
    # ------------------------------------------------------------

    construction = MasonryParameters(
        foundation_width_m=0.600,
        foundation_depth_m=0.600,
        foundation_concrete_thickness_m=0.100,
        slab_thickness_m=0.125,
        hardcore_depth_m=0.150,
        blinding_thickness_m=0.050,
    )

    assert construction.foundation_width_m == 0.600
    assert construction.foundation_depth_m == 0.600
    assert construction.foundation_concrete_thickness_m == 0.100

    assert construction.slab_thickness_m == 0.125
    assert construction.hardcore_depth_m == 0.150
    assert construction.blinding_thickness_m == 0.050

    print("Construction parameters: PASS")

    # ------------------------------------------------------------
    # Material quantity
    # ------------------------------------------------------------

    cement = MaterialQuantity(
        material_name="Cement",
        quantity=20.0,
        unit="bag",
        material_id=CEMENT,
        category="Cement",
        source="foundation calculation",
    )

    assert cement.material_name == "Cement"
    assert cement.quantity == 20.0
    assert cement.unit == "bag"
    assert cement.material_id == CEMENT

    print("MaterialQuantity: PASS")

    # ------------------------------------------------------------
    # Stage material quantity
    # ------------------------------------------------------------

    footing_cement = StageMaterialQuantity(
        stage_id=STAGE_FOOTING,
        stage_name="Footing",
        material_id=CEMENT,
        material_name="Cement",
        quantity=20.0,
        unit="bag",
        category="Cement",
        source="foundation calculation",
    )

    assert footing_cement.stage_id == STAGE_FOOTING
    assert footing_cement.material_id == CEMENT
    assert footing_cement.quantity == 20.0

    print("StageMaterialQuantity: PASS")

    # ------------------------------------------------------------
    # Stage material summary
    # ------------------------------------------------------------

    summary = StageMaterialSummary()

    summary.add(
        footing_cement
    )

    summary.add(
        StageMaterialQuantity(
            stage_id=STAGE_FOOTING,
            stage_name="Footing",
            material_id=BUILDING_SAND,
            material_name="Building sand",
            quantity=2.0,
            unit="m3",
            category="Aggregates",
        )
    )

    summary.add(
        StageMaterialQuantity(
            stage_id=STAGE_SLAB,
            stage_name="Slab",
            material_id=CEMENT,
            material_name="Cement",
            quantity=15.0,
            unit="bag",
            category="Cement",
        )
    )

    assert summary.total_quantity_records == 3

    footing_materials = summary.get_stage(
        STAGE_FOOTING
    )

    assert len(footing_materials) == 2

    cement_materials = summary.get_material(
        CEMENT
    )

    assert len(cement_materials) == 2

    print("StageMaterialSummary: PASS")

    # ------------------------------------------------------------
    # Standard material identifiers
    # ------------------------------------------------------------

    assert STANDARD_BRICK == "standard_brick"
    assert CEMENT == "cement_50kg"
    assert BUILDING_SAND == "building_sand"
    assert QUARRY_STONE == "quarry_stone"
    assert CONSTRUCTION_WATER == "construction_water"
    assert HARDCORE == "hardcore"
    assert DPM == "dpm"
    assert LINTEL == "lintel"
    assert NAILS == "nails"

    print("Material identifiers: PASS")

    # ------------------------------------------------------------
    # Roofing identifiers remain available for compatibility
    # ------------------------------------------------------------

    assert STAGE_ROOFING == "roofing"
    assert FIBRE_CEMENT_SHEET == "fibre_cement_sheet"
    assert TIMBER_POLE == "timber_pole_6m"

    print("Legacy roofing identifiers: PASS")

    # ------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------

    print("-" * 70)
    print("ALL MATERIAL MODEL TESTS PASSED")
    print("-" * 70)


if __name__ == "__main__":
    _run_tests()