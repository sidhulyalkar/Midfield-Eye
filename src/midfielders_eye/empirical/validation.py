from __future__ import annotations

from .schemas import EvidenceRecord, EvidenceTier


class ClaimBoundaryError(ValueError):
    pass


_DIRECT_ONLY = {
    "literal_gaze_direction",
    "fixation",
    "saccade",
    "joint_force",
    "ground_reaction_force",
    "center_of_pressure",
    "muscle_activation",
}


def validate_claim(record: EvidenceRecord, claimed_fields: set[str]) -> None:
    unavailable = claimed_fields - set(record.measured_fields) - set(record.inferred_fields)
    if unavailable:
        raise ClaimBoundaryError(f"evidence record does not contain fields: {sorted(unavailable)}")
    direct_claims = claimed_fields & _DIRECT_ONLY
    if direct_claims and record.tier != EvidenceTier.DIRECT_MEASUREMENT:
        raise ClaimBoundaryError(
            f"direct-measurement language is not permitted for {record.tier.value}: {sorted(direct_claims)}"
        )
    inferred_as_measured = claimed_fields & set(record.inferred_fields) & _DIRECT_ONLY
    if inferred_as_measured:
        raise ClaimBoundaryError(f"inferred fields cannot be presented as measured: {sorted(inferred_as_measured)}")
