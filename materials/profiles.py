from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ConstructionProfile:
    """
    Represents a simple construction profile presented to the user.

    The user selects construction types using simple names.
    Technical parameters remain inside the material engine.
    """

    profile_id: str
    name: str

    wall_type: str
    roof_type: str
    window_type: str
    door_type: str
    floor_type: str
    ceiling_type: str


STANDARD_CONSTRUCTION_PROFILE = ConstructionProfile(
    profile_id="standard",
    name="Standard Construction",

    wall_type="standard_brick",
    roof_type="standard_fibre_cement",
    window_type="standard_aluminium",
    door_type="standard",
    floor_type="standard_concrete",
    ceiling_type="standard",
)


CONSTRUCTION_PROFILES: Dict[str, ConstructionProfile] = {
    STANDARD_CONSTRUCTION_PROFILE.profile_id:
        STANDARD_CONSTRUCTION_PROFILE,
}


def get_construction_profile(
    profile_id: str = "standard",
) -> ConstructionProfile:
    """
    Retrieve a construction profile by its ID.

    The standard profile is used by default.
    """

    try:
        return CONSTRUCTION_PROFILES[profile_id]
    except KeyError as exc:
        available = ", ".join(CONSTRUCTION_PROFILES.keys())

        raise ValueError(
            f"Unknown construction profile '{profile_id}'. "
            f"Available profiles: {available}"
        ) from exc