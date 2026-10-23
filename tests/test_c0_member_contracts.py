"""C0 source-model contract regressions, NOT check_column approval."""
from dataclasses import replace
import unittest
from examples.section_pilot import fixture_problem
from tbdy_column_core.domain.member_models import (
    PhysicalColumn,PhysicalEnd,RectangularTie,Crosstie,TransverseRegion,RebarCage,
    ColumnCandidate,SignedMemberDemand,MemberDemandPopulation
)
from tbdy_column_core.domain.identity import RevisionRef
from tbdy_column_core.domain.quantities import Length,Force,Moment
from tbdy_column_core.domain.coordinates import Point3D,ActionVector
from tbdy_column_core.domain.stations import StationRef,StepIdentity,StepKind,ResponseKey


class C0Tests(unittest.TestCase):
    def setUp(self):
        self.p=fixture_problem(layout="B")
        L=Length.mm
        self.member=PhysicalColumn(RevisionRef("member","C101","r1"),self.p.section.ref,
            Point3D(L(0),L(0),L(0)),Point3D(L(0),L(0),L(3000)),"BOT","TOP")
        self.tie=RectangularTie("T1",L(10),L(-150),L(150),L(-250),L(250))
        bars=self.p.section.longitudinal.bars
        cross=Crosstie("CT1",bars[0].bar_id,bars[1].bar_id,L(10))
        regions=(TransverseRegion("R1",L(0),L(1000),L(100),"T1",("CT1",)),
                 TransverseRegion("R2",L(1000),L(3000),L(150),"T1",()))
        self.cage=RebarCage(RevisionRef("cage","C101","r1"),self.p.section,(self.tie,),(cross,),regions)
        self.candidate=ColumnCandidate(RevisionRef("candidate","C101","r1"),self.member.ref,self.cage)

    def test_physical_end_separated_from_analysis_and_real_cage(self):
        self.assertEqual(self.member.centreline_length.as_mm,3000)
        self.assertEqual(self.member.face(PhysicalEnd.BOTTOM),"BOT")
        self.candidate.validate_for(self.member)

    def test_cage_amendment_requires_new_revision(self):
        new=self.candidate.with_cage(self.cage,RevisionRef("candidate","C101","r2"))
        self.assertNotEqual(new.ref,self.candidate.ref)
        with self.assertRaises(ValueError):
            self.candidate.with_cage(self.cage,self.candidate.ref)

    def test_missing_physical_region_is_not_assumed(self):
        short=replace(self.cage,regions=(self.cage.regions[0],
            replace(self.cage.regions[1],finish=Length.mm(2800))))
        with self.assertRaises(ValueError):
            short.validate_for(self.member)
        with self.assertRaises(ValueError):
            replace(self.cage,regions=(self.cage.regions[0],
                replace(self.cage.regions[1],start=Length.mm(1100))))

    def test_crosstie_must_point_to_real_selected_bars(self):
        bad=replace(self.cage.crossties[0],first_bar_id="ghost")
        with self.assertRaises(ValueError):
            replace(self.cage,crossties=(bad,))

    def test_response_keys_preserve_both_faces_at_same_station(self):
        s=StationRef("map1","C101","E1","s0","I","face1")
        k=ResponseKey("run","generation","LC1",StepIdentity(StepKind.SINGLE),s,"P-M2-M3")
        k2=replace(k,station=replace(s,reference_face_id="face2"))
        v=MemberDemandPopulation(self.member.ref,(k,k2),())
        self.assertEqual(len(v.missing_keys),2)
        self.assertFalse(v.is_complete)

    def test_envelope_maximum_cannot_be_signed_coincident_vector(self):
        s=StationRef("map1","C101","E1","s0","I","face1")
        k=ResponseKey("run","generation","LC1",StepIdentity(StepKind.SINGLE),s,"P-M2-M3")
        act=ActionVector(Force.n(-500000),Force.n(0),Force.n(0),
                         Moment.nmm(0),Moment.nmm(1000000),Moment.nmm(2000000))
        d=SignedMemberDemand(k,act,self.p.frame_model_contract.frame,self.p.input_refs[0])
        self.assertTrue(MemberDemandPopulation(self.member.ref,(k,),(d,)).is_complete)
        with self.assertRaises(ValueError):
            SignedMemberDemand(replace(k,step=StepIdentity(StepKind.ENVELOPE_MAX)),
                               act,self.p.frame_model_contract.frame,self.p.input_refs[0])
