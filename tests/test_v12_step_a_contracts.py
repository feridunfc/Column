"""v1.2 A — dimensional and evidence contracts."""
from dataclasses import replace
import unittest
from tbdy_column_core.domain.quantities import Length,Area,Inertia,LengthSquared,Force,Moment,Stress,ElasticModulus
from tbdy_column_core.domain.tolerances import NumericalPolicy
from tbdy_column_core.domain.normative_state import NotRequired,Missing
from tbdy_column_core.domain.coordinates import Point3D,LocalFrame
from tbdy_column_core.domain.stations import StationRef,StationGeometry,StepIdentity,ResponseKey
from tbdy_column_core.domain.analysis_bundle import AnalysisRun,AnalysisBundle,SourceOrigin,ResponseSemantics,QualificationStatus
from tbdy_column_core.domain.outcomes import CheckResult,CoverageLedger,ApplicabilityStatus,ExecutionStatus,ComplianceStatus,FreshnessStatus

class QuantityContracts(unittest.TestCase):
    def test_canonical_operations(self):
        f=Stress.mpa(10)*Area.cm2(100)
        self.assertEqual(f,Force.kn(100))
        self.assertEqual(f*Length.cm(20),Moment.kn_cm(2000))
        self.assertEqual(Length.cm(20)*f,Moment.kn_m(20))
        self.assertEqual((Inertia.mm4(20000)/Area.mm2(200)).sqrt(),Length.mm(10))
    def test_incompatible_dimensions(self):
        for call in (lambda:Force.n(1)+Moment.nmm(1),
                     lambda:Area.mm2(1)+LengthSquared.mm2(1),
                     lambda:Stress.mpa(1)+Force.n(1)):
            with self.assertRaises(TypeError):call()
    def test_signed_invalid_and_roundtrip(self):
        self.assertEqual(Force.kn(-2).as_n,-2000)
        self.assertEqual(Length.cm(40),Length.mm(400))
        for ctor,v in ((Length.mm,True),(Force.n,float("nan")),(Moment.nmm,float("inf"))):
            with self.assertRaises((TypeError,ValueError)):ctor(v)
    def test_policy_type_and_geometry(self):
        p=NumericalPolicy(Length.mm(.001),Force.n(1),Moment.nmm(100),1e-6)
        with self.assertRaises(TypeError):replace(p,relative_tol=Length.mm(1))
        with self.assertRaises(TypeError):replace(p,force_balance_tol=1.)

class IdentityContracts(unittest.TestCase):
    def test_handedness_and_reflection(self):
        p=Point3D(Length.mm(0),Length.mm(0),Length.mm(0))
        local=LocalFrame(p,(1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
        self.assertEqual(local.to_local_vector((1,2,3)),(1.,2.,3.))
        with self.assertRaises(ValueError):
            LocalFrame(p,(1.,0.,0.),(0.,1.,0.),(0.,0.,-1.))
    def test_station_float_not_identity(self):
        x=StationRef("MAP","MEM","E1","S1","LEFT")
        y=replace(x,section_side="RIGHT")
        self.assertEqual(len({x,y}),2)
        pos=Point3D(Length.mm(0),Length.mm(0),Length.mm(0))
        a=StationGeometry(x,Length.mm(100),Length.mm(100),Length.mm(100),pos,"LF",Length.mm(.1))
        b=replace(a,station_ref=y)
        self.assertEqual(a.physical_station,b.physical_station)
        k=ResponseKey("R1","G1","LC1",StepIdentity("SingleValue"),"S1","P")
        self.assertNotEqual(k,replace(k,result_generation_id="G2"))
        self.assertNotEqual(k,replace(k,step_identity=StepIdentity("TimeStep",1)))
    def test_norequired_requires_evidence(self):
        with self.assertRaises(ValueError):NotRequired("","because","")
        self.assertEqual(Missing("beam","SCWB","native").field_name,"beam")

class BundleAndResults(unittest.TestCase):
    def test_mixed_runs_do_not_auto_qualify(self):
        a=AnalysisRun("A","M","G1",SourceOrigin.RECORDED,ResponseSemantics.SIGNED_STATIC,QualificationStatus.VERIFIED,"B")
        b=replace(a,run_id="B",result_generation_id="G2")
        self.assertTrue(AnalysisBundle((("forces",a),)).is_qualified)
        self.assertFalse(AnalysisBundle((("forces",a),("story",b))).is_qualified)
        self.assertFalse(AnalysisBundle((("forces",a),("story",b)),("link",),("open",)).is_qualified)
        self.assertFalse(AnalysisBundle((("forces",a),("story",replace(b,model_revision_id="NEW"))),("link",)).is_qualified)
    def test_partial_coverage_cannot_pass(self):
        partial=CoverageLedger(("A","B"),("A",))
        with self.assertRaises(ValueError):
            CheckResult("PMM",ApplicabilityStatus.APPLIES,ExecutionStatus.COMPLETED,
                        ComplianceStatus.PASS,partial,FreshnessStatus.CURRENT,"REF","incomplete")
        self.assertFalse(CheckResult("PMM",ApplicabilityStatus.APPLIES,ExecutionStatus.MISSING_INPUT,
                        ComplianceStatus.NOT_EVALUATED,partial,FreshnessStatus.UNKNOWN,"REF","missing").coverage.is_complete)

if __name__=="__main__":unittest.main()
