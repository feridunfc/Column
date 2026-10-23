"""v1.3.1 A contracts — engineering-risk examples, not constructor counts."""
from dataclasses import replace
from pathlib import Path
import ast
import unittest
from tbdy_column_core.domain.quantities import (
    Length,Area,LengthSquared,Inertia,Force,Moment,Stress,ElasticModulus,Angle,
)
from tbdy_column_core.domain.tolerances import NumericalPolicy,within
from tbdy_column_core.domain.coordinates import (
    Point3D,LocalFrame,ActionVector,AxialSignConvention,
    transform_action,kernel_compression_n,
)
from tbdy_column_core.domain.identity import SourceRef,RuleRef,RevisionRef,EvidenceRef
from tbdy_column_core.domain.stations import (
    StationRef,StationGeometry,StepIdentity,StepKind,ResponseKey,
)
from tbdy_column_core.domain.analysis_bundle import (
    SourceMetadata,ResponseSemantics,AnalysisRun,RoleBinding,RequiredRole,
    VerifiedScope,VerifiedCompatibility,EvidenceCatalog,AnalysisBundle,
)
from tbdy_column_core.domain.normative_state import (
    Provided,NotRequired,Missing,Unsupported,Unresolved,not_required_is_supported,
)
from tbdy_column_core.domain.outcomes import (
    CoverageLedger,CheckResult,Applicability,Execution,Compliance,Freshness,
)


def fixture_frame(origin=(0,0,0), axes=((1,0,0),(0,1,0),(0,0,1))):
    return LocalFrame(Point3D(*(Length.mm(v) for v in origin)),
                      *(tuple(float(x) for x in row) for row in axes))


def evidence(eid="E1"):
    return EvidenceRef(eid,SourceRef("ETABS","recorded.zip","row:7","kN,m","capture:1"),
                       RevisionRef("column","P","M1"))


class UnitsAndPolicy(unittest.TestCase):
    def test_dimensional_chain_from_cm_and_mpa(self):
        self.assertEqual(Stress.mpa(10)*Area.cm2(100),Force.kn(100))
        self.assertEqual(Area.cm2(100)*Stress.mpa(10),Force.kn(100))
        self.assertEqual(Force.kn(100)*Length.cm(20),Moment.kn_m(20))
        self.assertEqual(Length.cm(20)*Force.kn(100),Moment.kn_cm(2000))
        self.assertEqual((Inertia.mm4(100_000)/Area.mm2(1000)).sqrt(),Length.mm(10))
        self.assertAlmostEqual(Angle.deg(180).as_rad,3.141592653589793,places=14)
        self.assertEqual(Length.m(0.4),Length.cm(40))
        self.assertTrue(within(1.00000001,1.0,1e-7,0.0))

    def test_incompatible_and_implicit_conversion_rejected(self):
        for f in (lambda: Force.n(1)+Moment.nmm(1),
                  lambda: Area.mm2(1)+LengthSquared.mm2(1),
                  lambda: Force.n(1)*Area.mm2(1),
                  lambda: float(Force.n(1)),
                  lambda: ElasticModulus.mpa(200_000)+Stress.mpa(5)):
            with self.assertRaises(TypeError): f()

    def test_bool_nan_inf_and_arithmetic_overflow_rejected(self):
        for f in (lambda: Length.mm(True),lambda: Force.n(float("nan")),
                  lambda: Moment.kn_m(float("inf")),
                  lambda: Length.m(1e308),
                  lambda: Force.n(1e308)*1e308,
                  lambda: Force.n(1)/False):
            with self.assertRaises((TypeError,ValueError)): f()
        self.assertEqual(Force.kn(-4).as_n,-4000)
        self.assertEqual(Moment.kn_m(-2).as_nmm,-2_000_000)

    def test_typed_absolute_and_relative_policy(self):
        policy=NumericalPolicy(Length.mm(.001),1e-10,Force.n(1),
                               Moment.nmm(2000),0.0)
        self.assertEqual(policy.relative_tol,0)
        for change in ({"geometric_tol":.001},{"relative_tol":-1e-3},
                       {"force_balance_tol":1.0},{"axis_tol":0},
                       {"angle_count":True},{"max_iterations":False}):
            with self.assertRaises((TypeError,ValueError)):
                replace(policy,**change)


class CoordinateAndStation(unittest.TestCase):
    def test_right_handed_axis_rotation_and_inverse(self):
        base=fixture_frame()
        rotated=fixture_frame(axes=((1,0,0),(0,0,1),(0,-1,0)))
        self.assertEqual(rotated.to_local((0,1,0)),(0.,0.,-1.))
        self.assertEqual(rotated.to_global((0,0,-1)),(0.,1.,0.))
        with self.assertRaises(ValueError):
            fixture_frame(axes=((1,0,0),(0,1,0),(0,0,-1)))
        with self.assertRaises(ValueError):
            fixture_frame(axes=((1,0,0),(1,0,0),(0,0,1)))

    def test_six_action_transfer_reference_r_cross_f_and_inverse(self):
        src=fixture_frame(origin=(100,200,0))
        dst=fixture_frame()
        action=ActionVector(Force.kn(100),Force.n(0),Force.n(0),
                            Moment.nmm(0),Moment.kn_m(5),Moment.nmm(0))
        moved=transform_action(action,src,dst)
        # r=(100,200,0) mm and F=(100000,0,0) N -> M3=-20,000,000 Nmm
        self.assertEqual(moved.m3,Moment.kn_m(-20))
        self.assertEqual(moved.m2,Moment.kn_m(5))
        self.assertEqual(transform_action(moved,dst,src),action)
        self.assertEqual(kernel_compression_n(action,
            AxialSignConvention.F1_COMPRESSION_POSITIVE),Force.kn(100))
        self.assertEqual(kernel_compression_n(action,
            AxialSignConvention.F1_TENSION_POSITIVE),Force.kn(-100))
        with self.assertRaises(TypeError):kernel_compression_n(action,None)

    def test_different_faces_same_position_not_deduplicated(self):
        left=StationRef("MAP-V1","MEM-C","E1","S1","LEFT","FACE-1")
        right=replace(left,section_side="RIGHT")
        self.assertEqual(len({left,right}),2)
        pt=Point3D(Length.mm(1),Length.mm(2),Length.mm(3))
        a=StationGeometry(left,Length.mm(100),Length.mm(100),
                          Length.mm(100),pt,"FRAME",Length.mm(.001))
        b=replace(a,ref=right)
        self.assertEqual(a.position,b.position)
        self.assertNotEqual(a.ref,b.ref)
        k=ResponseKey("R","G","LC1",StepIdentity(StepKind.SINGLE),
                      left,"P")
        self.assertNotEqual(k,replace(k,station=right))
        self.assertNotEqual(k,replace(k,result_generation_id="G2"))
        self.assertNotEqual(k,replace(k,step=StepIdentity(StepKind.ENVELOPE_MAX)))
        self.assertNotEqual(k,replace(k,step=StepIdentity(StepKind.TIME,0.1)))


class EvidenceAndOutcomes(unittest.TestCase):
    def setUp(self):
        self.source=SourceMetadata("ETABS","RECORDED_EXPORT","DESIGN",
                                   ResponseSemantics.SIGNED_STATIC)
        self.run=AnalysisRun("RUN-1","M1","GEN-1","BASIS-1",self.source,("LC1:I","LC1:J"))
        self.need=RequiredRole("DESIGN_FORCES","METH","PMM","M1",
              (ResponseSemantics.SIGNED_STATIC,),("LC1:I","LC1:J"))
        self.scope=VerifiedScope(evidence(),"DESIGN_FORCES","METH","PMM","M1",
             "RUN-1","M1","GEN-1",("LC1:I","LC1:J"),"VERIFIER:01")

    def test_present_data_does_not_qualify_itself(self):
        val=Provided(Force.kn(200),evidence())
        self.assertEqual(val.value.as_kn,200)
        self.assertEqual(AnalysisBundle((RoleBinding("DESIGN_FORCES",self.run),)).
                         qualify((self.need,),EvidenceCatalog()).issues,
                         ("DESIGN_FORCES:EVIDENCE_UNRESOLVED_OR_AMBIGUOUS",))

    def test_scoped_positive_same_run_and_wrong_scope(self):
        bundle=AnalysisBundle((RoleBinding("DESIGN_FORCES",self.run),))
        self.assertTrue(bundle.qualify((self.need,),
              EvidenceCatalog((self.scope,))).contract_ready)
        changed=replace(self.need,method_id="OTHER")
        self.assertFalse(bundle.qualify((changed,),
              EvidenceCatalog((self.scope,))).contract_ready)
        changed=replace(self.need,input_revision_id="M2")
        self.assertFalse(bundle.qualify((changed,),
              EvidenceCatalog((self.scope,))).contract_ready)
        changed=replace(self.need,consumer_id="STORY")
        self.assertFalse(bundle.qualify((changed,),
              EvidenceCatalog((self.scope,))).contract_ready)

    def test_same_run_different_role_and_semantics_not_automatic(self):
        bundle=AnalysisBundle((RoleBinding("DRIFT_REFERENCE",self.run),))
        self.assertFalse(bundle.qualify((replace(self.need,role="DRIFT_REFERENCE"),),
              EvidenceCatalog((self.scope,))).contract_ready)
        mismatch=replace(self.run,source=replace(
              self.source,response_semantics=ResponseSemantics.SPECTRAL))
        self.assertIn("DESIGN_FORCES:UNSUPPORTED_SEMANTICS",
            AnalysisBundle((RoleBinding("DESIGN_FORCES",mismatch),)).qualify(
                  (self.need,),EvidenceCatalog((self.scope,))).issues)

    def test_different_runs_need_resolved_compatibility(self):
        second=replace(self.run,run_id="RUN-2",result_generation_id="GEN-2")
        drift=replace(self.need,role="DRIFT_REFERENCE")
        proof2=replace(self.scope,evidence=evidence("E2"),
              role="DRIFT_REFERENCE",run_id="RUN-2",result_generation_id="GEN-2")
        b=AnalysisBundle((RoleBinding("DESIGN_FORCES",self.run),
                          RoleBinding("DRIFT_REFERENCE",second)))
        self.assertFalse(b.qualify((self.need,drift),
               EvidenceCatalog((self.scope,proof2))).contract_ready)
        comp=VerifiedCompatibility(evidence("E3"),("RUN-1","RUN-2"),
                  "METH","PMM","M1","VERIFIER:COMPAT")
        self.assertTrue(b.qualify((self.need,drift),
               EvidenceCatalog((self.scope,proof2),(comp,))).contract_ready)
        self.assertFalse(b.qualify((self.need,replace(drift,consumer_id="DIFFERENT")),
               EvidenceCatalog((self.scope,proof2),(comp,))).contract_ready)

    def test_notrequired_needs_resolved_role_specific_evidence(self):
        v=NotRequired("STABILITY",RuleRef("TS500","2000","7.6"),
                      "method inapplicable",evidence())
        self.assertFalse(not_required_is_supported(
             v,EvidenceCatalog(),method_id="METHOD",consumer_id="STORY",
             input_revision_id="M1"))
        proof=replace(self.scope,role="APPLICABILITY:STABILITY",
             method_id="METHOD",consumer_id="STORY",applicability_rule=v.rule)
        self.assertTrue(not_required_is_supported(
             v,EvidenceCatalog((proof,)),method_id="METHOD",
             consumer_id="STORY",input_revision_id="M1"))
        self.assertFalse(not_required_is_supported(
             v,EvidenceCatalog((proof,)),method_id="METHOD",
             consumer_id="OTHER",input_revision_id="M1"))

    def test_evidence_revision_and_producer_binding_fail_closed(self):
        b=AnalysisBundle((RoleBinding("DESIGN_FORCES",self.run),))
        with self.assertRaises(ValueError):
            replace(self.scope,evidence=EvidenceRef("OTHER",
                    self.scope.evidence.source,RevisionRef("column","P","M2")))
        wrong_producer=replace(
             self.scope,evidence=EvidenceRef("FOREIGN",
                 replace(self.scope.evidence.source,producer="OTHER"),
                 self.scope.evidence.input_revision))
        decision=b.qualify((self.need,),EvidenceCatalog((wrong_producer,)))
        self.assertFalse(decision.contract_ready)
        self.assertIn("DESIGN_FORCES:EVIDENCE_UNRESOLVED_OR_AMBIGUOUS",decision.issues)

    def test_notrequired_wrong_rule_and_revision_not_accepted(self):
        v=NotRequired("STABILITY",RuleRef("TS500","2000","7.6"),
                      "method inapplicable",evidence())
        wrong_rule=replace(self.scope,role="APPLICABILITY:STABILITY",
                     method_id="METHOD",consumer_id="STORY",
                     applicability_rule=RuleRef("OTHER","2000","7.6"))
        self.assertFalse(not_required_is_supported(
                     v,EvidenceCatalog((wrong_rule,)),
                     method_id="METHOD",consumer_id="STORY",input_revision_id="M1"))
        right_rule=replace(wrong_rule,applicability_rule=v.rule)
        self.assertTrue(not_required_is_supported(
                     v,EvidenceCatalog((right_rule,)),
                     method_id="METHOD",consumer_id="STORY",input_revision_id="M1"))
        self.assertFalse(not_required_is_supported(
                     v,EvidenceCatalog((right_rule,)),
                     method_id="METHOD",consumer_id="STORY",input_revision_id="M2"))

    def test_catalog_malformed_and_duplicate_role_rejected(self):
        with self.assertRaises(TypeError):
            EvidenceCatalog([self.scope])
        with self.assertRaises(ValueError):
            EvidenceCatalog((self.scope,self.scope))
        b=AnalysisBundle((RoleBinding("DESIGN_FORCES",self.run),))
        with self.assertRaises(ValueError):
            b.qualify((self.need,self.need),EvidenceCatalog((self.scope,)))

    def test_coverage_incomplete_known_fail_still_visible(self):
        c=CoverageLedger(("CASE1","CASE2"),("CASE1",))
        rule=RuleRef("TS500","2000","7.1")
        check=CheckResult("PMM","MEM1",Applicability.APPLIES,Execution.COMPLETED,
             Compliance.FAIL,c,Freshness.CURRENT,rule,"TRACE","known fail")
        self.assertEqual(check.compliance,Compliance.FAIL)
        self.assertFalse(check.coverage.is_complete)
        with self.assertRaises(ValueError):
            replace(check,compliance=Compliance.PASS)
        with self.assertRaises(ValueError):
            CoverageLedger((),())
        self.assertEqual(Missing("top_beam","SCWB","native").field_name,"top_beam")
        self.assertEqual(Unsupported("modal method","SPECTRAL","not implemented").method_id,
                         "SPECTRAL")
        self.assertEqual(Unresolved("model",("R1","R2"),"conflict").subject,"model")


class ImportBoundary(unittest.TestCase):
    def test_domain_has_no_hidden_outer_dependencies(self):
        root=Path(__file__).resolve().parents[1]/"tbdy_column_core"/"domain"
        forbidden=("physics","application","adapters","etabs","sqlite","tkinter",
                   "requests","httpx")
        for path in root.glob("*.py"):
            syntax=ast.parse(path.read_text(encoding="utf-8"))
            for item in ast.walk(syntax):
                if isinstance(item,ast.Import):
                    for imp in item.names:
                        self.assertFalse(any(x in imp.name.lower() for x in forbidden),
                                         (path,imp.name))
                elif isinstance(item,ast.ImportFrom):
                    target=(item.module or "").lower()
                    self.assertFalse(any(x in target for x in forbidden),
                                     (path,target))


if __name__ == "__main__":
    unittest.main()
