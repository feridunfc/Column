"""C2 physical member geometry and immutable scenario/trial checks only."""
from dataclasses import replace
import unittest

from examples.section_pilot import fixture_problem
from tbdy_column_core.domain.identity import RevisionRef, EvidenceRef, SourceRef, RuleRef
from tbdy_column_core.domain.quantities import Length
from tbdy_column_core.domain.coordinates import Point3D
from tbdy_column_core.domain.member_models import (
    PhysicalColumn, RectangularTie, TransverseRegion, RebarCage, ColumnCandidate,
)
from tbdy_column_core.domain.analysis_bundle import (
    AnalysisBundle, RoleBinding, AnalysisRun, SourceMetadata, ResponseSemantics,
)
from tbdy_column_core.domain.scenario import DesignScenario,TrialContext
from tbdy_column_core.engineering.member_mechanics import (
    LengthKind,DeclaredLength,MemberGeometryProblem,MemberMechanics,
)


class C2ScenarioAndGeometry(unittest.TestCase):
    def setUp(self):
        L=Length.mm
        p=fixture_problem(layout="B")
        self.member=PhysicalColumn(
            RevisionRef("member","C10","r1"),p.section.ref,
            Point3D(L(0),L(0),L(0)),Point3D(L(0),L(0),L(3000)),"bottom-face","top-face"
        )
        tie=RectangularTie("T1",p.section.longitudinal.tie_diameter,
                           L(-150),L(150),L(-250),L(250))
        cage=RebarCage(RevisionRef("cage","C10","r1"),
                         p.section,(tie,),(),(TransverseRegion(
                             "all",L(0),L(3000),L(150),"T1",()),))
        self.candidate=ColumnCandidate(RevisionRef("candidate","C10","r1"),
                                       self.member.ref,cage)
        source=SourceMetadata("ETABS_OFFLINE","recorded","test",ResponseSemantics.SIGNED_STATIC)
        run=AnalysisRun("run","model","gen","basis",source,("row1",))
        bundle=AnalysisBundle((RoleBinding("DESIGN_FORCES",run),))
        self.scenario=DesignScenario(RevisionRef("scenario","s","r1"),
            RevisionRef("model","m","r1"),RevisionRef("basis","b","r1"),
            bundle,(self.member,),(self.candidate,),("GEOMETRY","PMM","SHEAR"))
        self.trial=TrialContext(RevisionRef("trial","t","r1"),
                              self.scenario,self.member.ref,self.candidate)
        self.source=EvidenceRef("len-source",SourceRef("DRAWING","dim","1","mm","acq"),
                                RevisionRef("geometry","drawing","r1"))

    def fact(self,kind,value=2700,method=None):
        return DeclaredLength(kind,Length.mm(value),self.source,method)

    def test_centreline_not_auto_clear_or_effective(self):
        result=MemberMechanics.prepare_geometry(
            MemberGeometryProblem(self.trial,self.member.ref,()))
        self.assertEqual(result.centreline.as_mm,3000)
        self.assertEqual(result.bottom_face_id,"bottom-face")
        self.assertEqual(result.top_face_id,"top-face")
        self.assertEqual(result.missing_length_kinds,tuple(LengthKind))
        self.assertFalse(result.stiffness_ready)
        self.assertFalse(result.second_order_ready)

    def test_clear_and_unbraced_distinct_no_inference(self):
        facts=(self.fact(LengthKind.CLEAR,2600),
               self.fact(LengthKind.UNBRACED_LOCAL_2,2900))
        r=MemberMechanics.prepare_geometry(
            MemberGeometryProblem(self.trial,self.member.ref,facts))
        self.assertEqual(tuple(x.value.as_mm for x in r.supplied_lengths),(2600,2900))
        self.assertIn(LengthKind.UNBRACED_LOCAL_3,r.missing_length_kinds)
        self.assertIn(LengthKind.EFFECTIVE_LOCAL_2,r.missing_length_kinds)
        self.assertFalse(r.stiffness_ready)

    def test_effective_length_cannot_be_unqualified_numeric(self):
        with self.assertRaises(ValueError):
            self.fact(LengthKind.EFFECTIVE_LOCAL_2,3400)
        rule=RuleRef("TS500","2000","declared-geometry-method-not-verified")
        r=MemberMechanics.prepare_geometry(MemberGeometryProblem(
            self.trial,self.member.ref,
            (self.fact(LengthKind.EFFECTIVE_LOCAL_2,3400,rule),)))
        self.assertEqual(r.supplied_lengths[0].value.as_mm,3400)
        self.assertFalse(r.second_order_ready)

    def test_invalid_clear_and_duplicate_kind_fail_closed(self):
        with self.assertRaises(ValueError):
            MemberMechanics.prepare_geometry(MemberGeometryProblem(
                self.trial,self.member.ref,(self.fact(LengthKind.CLEAR,3400),)))
        with self.assertRaises(ValueError):
            MemberGeometryProblem(self.trial,self.member.ref,
                                  (self.fact(LengthKind.CLEAR),self.fact(LengthKind.CLEAR)))

    def test_target_trial_cannot_rebind_member_or_create_other_candidate(self):
        other=replace(self.member,ref=RevisionRef("member","OTHER","r1"))
        with self.assertRaises(ValueError):
            MemberGeometryProblem(self.trial,other.ref,())
        with self.assertRaises(ValueError):
            TrialContext(self.trial.ref,self.scenario,self.member.ref,replace(
                self.candidate,ref=RevisionRef("candidate","different","r2")))
        self.assertEqual(self.trial.resolve_candidate(self.member.ref),self.candidate)

    def test_scenario_rejects_incomplete_and_mismatched_assignments(self):
        with self.assertRaises(ValueError):
            replace(self.scenario,assignments=())
        with self.assertRaises(ValueError):
            replace(self.scenario,assignments=(self.candidate,self.candidate))
        with self.assertRaises(ValueError):
            replace(self.scenario,members=(self.member,self.member))

    def test_trial_new_candidate_revision_does_not_change_scenario(self):
        amended=self.candidate.with_cage(
            self.candidate.cage,RevisionRef("candidate","C10","r2"))
        trial=replace(self.trial,ref=RevisionRef("trial","t","r2"),
                      target_candidate=amended)
        self.assertEqual(trial.resolve_candidate(self.member.ref),amended)
        self.assertEqual(self.scenario.candidate_for(self.member.ref),self.candidate)
        self.assertEqual(MemberMechanics.prepare_geometry(
            MemberGeometryProblem(trial,self.member.ref,())).candidate_ref,amended.ref)
