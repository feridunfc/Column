"""B9 observed numerical quality probe. Prints evidence; never PASS."""
from __future__ import annotations
import json

from examples.section_pilot import fixture_problem
from tbdy_column_core.domain.section_requests import RadialCapacityAtAxialForce
from tbdy_column_core.domain.quantities import Force,Moment
from tbdy_column_core.engineering.triple_convergence import assess_three_level_radial_refinement


def main():
    problem=fixture_problem(layout="B",angle_count=72,
        request=RadialCapacityAtAxialForce(
            Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
    result=assess_three_level_radial_refinement(problem)
    record={
        "purpose":"NUMERICAL_REVIEW_ONLY",
        "layout":"B_400x600_6_D20",
        "target_compression_n":500000,
        "angle_counts":list(result.counts),
        "capacities_nmm":list(result.capacity_nmm),
        "successive_observed_deltas_nmm":list(result.differences_nmm),
        "declared_moment_budgets_nmm":list(result.moment_budgets_nmm),
        "numeric_verdict":result.verdict.value,
        "not_certified":["continuous angular truncation bound",
                         "globally unique root",
                         "TS500/TBDY full column code compliance"],
    }
    print(json.dumps(record,sort_keys=True,allow_nan=False))
    print("B9_NUMERIC_EVIDENCE_REVIEW_HOLD")


if __name__=="__main__":
    main()
