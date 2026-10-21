"""One audited, intentionally narrow TS 500 (2000) equation 7.13 gate.

phi = 1.5 * Delta_i / V_fi * sum(N_di / l_i).
<=0.05 supports the specified non-sway presumption, subject to source-basis validation.
>0.05 does NOT establish a normative 0.25 failure threshold and is not a full
second-order design conclusion. No response-spectrum shortcut is implemented.
"""
from __future__ import annotations

from .contracts import GateStatus, StoryStabilityFacts, StoryStabilityResult, validate_exact_population


def check_nonsway_ts500_7_13(facts: StoryStabilityFacts) -> StoryStabilityResult:
    blocker = validate_exact_population(facts)
    if blocker is not None:
        return StoryStabilityResult(
            story_id=facts.story_id,
            direction=facts.direction,
            rule_id="TS500:7.6.2.1:EQ7.13",
            status=GateStatus.EVIDENCE_BLOCKED,
            phi=None,
            reason=blocker,
            evidence=facts.evidence,
            denominator_column_count=len(facts.expected_column_ids),
            verified_column_count=len(facts.columns),
        )
    sum_ndi_over_li_n_per_mm = sum(col.ndi_n / col.li_mm for col in facts.columns)
    phi = 1.5 * facts.delta_i_mm * sum_ndi_over_li_n_per_mm / facts.v_fi_n
    is_nonsway = phi <= 0.05
    return StoryStabilityResult(
        story_id=facts.story_id,
        direction=facts.direction,
        rule_id="TS500:7.6.2.1:EQ7.13",
        status=GateStatus.NONSWAY_ESTABLISHED if is_nonsway else GateStatus.NONSWAY_NOT_ESTABLISHED,
        phi=phi,
        reason=("EQUATION_7_13_WITHIN_0_05" if is_nonsway else "EQUATION_7_13_EXCEEDS_0_05_REQUIRE_OTHER_APPROVED_SECOND_ORDER_PATH"),
        evidence=facts.evidence,
        denominator_column_count=len(facts.expected_column_ids),
        verified_column_count=len(facts.columns),
    )
