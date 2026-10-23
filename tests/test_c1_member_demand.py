"""C1: source qualification, signed 6-vector transport and physical station census."""
from dataclasses import replace
import unittest
from examples.section_pilot import fixture_problem
from tbdy_column_core.domain.identity import RevisionRef,EvidenceRef,SourceRef
from tbdy_column_core.domain.quantities import Length,Force,Moment
from tbdy_column_core.domain.coordinates import Point3D,ActionVector,AxialSignConvention
from tbdy_column_core.domain.stations import StationRef,StationGeometry,StepIdentity,StepKind,ResponseKey
from tbdy_column_core.domain.analysis_bundle import (
    SourceMetadata,ResponseSemantics,AnalysisRun,RequiredRole,VerifiedScope,
    EvidenceCatalog,RoleBinding,AnalysisBundle,
)
from tbdy_column_core.domain.member_models import (
    PhysicalColumn,RectangularTie,Crosstie,TransverseRegion,RebarCage,
    ColumnCandidate,SignedMemberDemand,MemberDemandPopulation,
)
from tbdy_column_core.engineering.member_demand import (
    StationDemandBinding,MemberDemandCompileProblem,MemberDemandCompiler,DemandCompileStatus,
)


class C1DemandTests(unittest.TestCase):
    def setUp(self):
        L=Length.mm
        self.p=fixture_problem(layout="B")
        self.member=PhysicalColumn(
            RevisionRef("member","C101","r1"),self.p.section.ref,
            Point3D(L(0),L(0),L(0)),Point3D(L(0),L(0),L(3000)),"BOT","TOP")
        tie=RectangularTie("T1",L(10),L(-150),L(150),L(-250),L(250))
        bars=self.p.section.longitudinal.bars
        cross=Crosstie("CT1",bars[0].bar_id,bars[1].bar_id,L(10))
        region=TransverseRegion("R1",L(0),L(3000),L(150),"T1",("CT1",))
        cage=RebarCage(RevisionRef("cage","C101","r1"),self.p.section,(tie,),(cross,),(region,))
        self.candidate=ColumnCandidate(RevisionRef("candidate","C101","r1"),self.member.ref,cage)
        frame=self.p.frame_model_contract.frame
        source_frame=replace(frame,origin=Point3D(L(100),L(0),L(0)))
        s=StationRef("map1","C101","E1","s0","I","BOT","BOTTOM")
        k=ResponseKey("run1","gen1","LC1",StepIdentity(StepKind.SINGLE),s,"P-M2-M3")
        e=EvidenceRef("raw-row",SourceRef("ETABS_OFFLINE","table","row01","N,Nmm","acq1"),
                      RevisionRef("analysis-input","run1","rev1"))
        act=ActionVector(Force.n(500000),Force.n(1000),Force.n(0),
                         Moment.nmm(0),Moment.nmm(0),Moment.nmm(0))
        dem=SignedMemberDemand(k,act,source_frame,e)
        self.pop=MemberDemandPopulation(self.member.ref,(k,),(dem,))
        geom=StationGeometry(s,L(0),L(0),L(0),self.member.bottom,"target",L(1))
        bind=StationDemandBinding(k,"row01",geom,frame,"target")
        source=SourceMetadata("ETABS_OFFLINE","table_archive","signed_members",
                              ResponseSemantics.SIGNED_STATIC)
        run=AnalysisRun("run1","model1","gen1","basis1",source,("row01",))
        self.role=RequiredRole("COLUMN_DEMAND","station_compile_v1","C1",
            "rev1",(ResponseSemantics.SIGNED_STATIC,),("row01",))
        proof_e=EvidenceRef("verified-run",SourceRef("ETABS_OFFLINE","table","manifest","N,Nmm","acq1"),
                            RevisionRef("analysis-input","run1","rev1"))
        proof=VerifiedScope(proof_e,"COLUMN_DEMAND","station_compile_v1","C1","rev1",
                           "run1","model1","gen1",("row01",),"receipt1")
        self.problem=MemberDemandCompileProblem(
            self.member,self.candidate,self.pop,(bind,),
            AnalysisBundle((RoleBinding("COLUMN_DEMAND",run),)),
            self.role,EvidenceCatalog((proof,),()),AxialSignConvention.F1_COMPRESSION_POSITIVE)

    def test_qualified_signed_transfer_includes_r_cross_f(self):
        out=MemberDemandCompiler.compile(self.problem)
        self.assertEqual(out.status,DemandCompileStatus.READY_FIRST_ORDER_ONLY,out.issues)
        self.assertEqual(out.missing_keys,())
        self.assertEqual(len(out.records),1)
        self.assertAlmostEqual(out.records[0].local_action.m3.as_nmm,100000)
        self.assertEqual(out.records[0].n_compression.as_n,500000)
        self.assertEqual(out.matched_qualification_evidence,("verified-run",))
        self.assertEqual(out.second_order_status,"NOT_EVALUATED")
        self.assertFalse(out.full_column_pass)

    def test_population_missing_keeps_independent_signed_row(self):
        L=Length.mm
        p=self.problem
        s2=replace(p.population.expected_keys[0].station,station_id="s1",
                   reference_face_id="TOP",physical_role="TOP")
        k2=replace(p.population.expected_keys[0],station=s2)
        geom2=StationGeometry(s2,L(3000),L(3000),L(3000),
                              self.member.top,"target",L(1))
        frame2=replace(self.p.frame_model_contract.frame,origin=self.member.top)
        b2=StationDemandBinding(k2,"row02",geom2,frame2,"target")
        full_pop=MemberDemandPopulation(self.member.ref,
                                       (p.population.expected_keys[0],k2),p.population.supplied)
        run=replace(p.analysis_bundle.bindings[0].run,population_keys=("row01","row02"))
        bundle=AnalysisBundle((RoleBinding("COLUMN_DEMAND",run),))
        role=replace(p.required_role,expected_population=("row01","row02"))
        proof=replace(p.evidence_catalog.scopes[0],population_keys=("row01","row02"))
        amended=replace(p,population=full_pop,
            station_bindings=p.station_bindings+(b2,),analysis_bundle=bundle,
            required_role=role,evidence_catalog=EvidenceCatalog((proof,),()))
        out=MemberDemandCompiler.compile(amended)
        self.assertEqual(out.status,DemandCompileStatus.INCOMPLETE_SOURCE)
        self.assertEqual(out.missing_keys,(k2,))
        self.assertEqual(len(out.records),1)
        self.assertFalse(out.full_column_pass)

    def test_missing_external_verification_refuses_transforms(self):
        out=MemberDemandCompiler.compile(replace(
            self.problem,evidence_catalog=EvidenceCatalog()))
        self.assertEqual(out.status,DemandCompileStatus.UNQUALIFIED_SOURCE)
        self.assertFalse(out.records)

    def test_source_run_and_row_identity_fail_closed(self):
        wrong_run=replace(self.problem.population.supplied[0].key,run_id="wrong")
        # Missing/changed ResponseKey cannot be joined with declared
        # expected key and therefore rejected at population construction.
        with self.assertRaises(ValueError):
            replace(self.problem.population,supplied=(
                replace(self.problem.population.supplied[0],key=wrong_run),))
        raw=self.problem.population.supplied[0]
        forged=replace(raw,evidence=replace(raw.evidence,source=replace(
            raw.evidence.source,record_identifier="unrelated")))
        out=MemberDemandCompiler.compile(replace(self.problem,population=replace(
            self.problem.population,supplied=(forged,))))
        self.assertEqual(out.status,DemandCompileStatus.UNQUALIFIED_SOURCE)

    def test_wrong_physical_face_is_not_swapped_from_i_j(self):
        binding=self.problem.station_bindings[0]
        pos=replace(binding.geometry,position=self.member.top,
                    physical_station=Length.mm(3000),obj_station=Length.mm(3000),
                    elm_station=Length.mm(3000))
        target=replace(binding.target_frame,origin=self.member.top)
        altered=replace(binding,geometry=pos,target_frame=target)
        out=MemberDemandCompiler.compile(replace(self.problem,station_bindings=(altered,)))
        self.assertEqual(out.status,DemandCompileStatus.INVALID_STATION_MAPPING)
        self.assertIn("WRONG_BOTTOM_FACE",out.issues[0])

    def test_tension_positive_external_sign_is_applied_once(self):
        out=MemberDemandCompiler.compile(replace(
            self.problem,axial_sign=AxialSignConvention.F1_TENSION_POSITIVE))
        self.assertEqual(out.records[0].n_compression.as_n,-500000)
