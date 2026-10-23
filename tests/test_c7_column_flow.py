"""C7 candidate tests authored for final batch; not executed here.

The analytical r x F check derives from source geometry, not a B solver
expected result. Section radial observation never establishes code PASS.
"""
import json
import unittest
from dataclasses import replace

import test_c1_member_demand as c1
from tbdy_column_core.domain.identity import RevisionRef,RuleRef
from tbdy_column_core.domain.scenario import DesignScenario,TrialContext
from tbdy_column_core.domain.stations import StepKind
from tbdy_column_core.domain.coordinates import transform_action
from tbdy_column_core.engineering.member_mechanics import MemberGeometryProblem
from tbdy_column_core.engineering.stability import BendingAxis,EffectScale
from tbdy_column_core.engineering.full_member_demand import (
    EffectBranchKey,SourceEffectAction,FullDemandCompileProblem,
)
from tbdy_column_core.engineering.column_evaluator import RequiredColumnCheck
from tbdy_column_core.application.column_check import CheckRequest,check_column
from tbdy_column_core.reporting.column_report import column_payload,column_json,column_html


class C7ColumnIntegration(unittest.TestCase):
    def setUp(self):
        self.fx=c1.C1DemandTests("test_qualified_signed_transfer_includes_r_cross_f")
        self.fx.setUp()
        p=self.fx.problem
        self.key=p.population.expected_keys[0]
        self.rule=RuleRef("PROVISIONAL","draft","NEEDS_AUTHORIZED_METHOD")
        scopes=("GEOMETRY","PMM","SECOND_ORDER","SHEAR","CONFINEMENT","JOINT")
        scenario=DesignScenario(
            RevisionRef("scenario","s","r1"),
            RevisionRef("model","m","r1"),
            RevisionRef("basis","b","r1"),
            p.analysis_bundle,(p.member,),(p.candidate,),scopes)
        self.trial=TrialContext(RevisionRef("trial","t","r1"),
                                scenario,p.member.ref,p.candidate)
        branches=tuple(EffectBranchKey(self.key,scale,axis,self.rule)
                       for scale in EffectScale for axis in BendingAxis)
        checks=tuple(RequiredColumnCheck(scope,self.rule,(
            ("PHYSICAL_GEOMETRY",) if scope=="GEOMETRY" else
            (repr(self.key),) if scope=="PMM" else
            (scope+"_REQUIRED",)
        )) for scope in scopes)
        evidence=self.fx.p.input_refs+(p.population.supplied[0].evidence,)
        self.request=CheckRequest(
            self.trial,MemberGeometryProblem(self.trial,p.member.ref,()),
            (),(),(),FullDemandCompileProblem(p,branches,()),
            checks,self.fx.p.numerical_policy,evidence)

    def test_independent_analytic_moment_transport(self):
        row=self.fx.problem.population.supplied[0]
        station=self.fx.problem.station_bindings[0]
        observed=transform_action(row.action,row.source_frame,station.target_frame)
        self.assertAlmostEqual(observed.m3.as_nmm,1000*100)
        self.assertEqual(row.action.m3.as_nmm,0)

    def test_full_column_scope_retained_without_false_pass(self):
        result=check_column(self.request)
        self.assertEqual(len(result.assessment.checks),6)
        self.assertEqual(len(result.assessment.missing_scopes),6)
        self.assertFalse(result.full_column_design_pass)
        self.assertFalse(result.assessment.is_complete)
        self.assertEqual(len(result.demands.missing_effect_branches),4)
        self.assertTrue(all(c.compliance.value=="NOT_EVALUATED"
                            for c in result.assessment.checks))
        self.assertFalse(result.mechanics.second_order_computed)

    def test_sampled_numeric_observation_is_not_pmm_code_approval(self):
        result=check_column(self.request)
        self.assertEqual(len(result.assessment.observations),1)
        obs=result.assessment.observations[0]
        self.assertEqual(obs.source_key,self.key)
        self.assertFalse(obs.numerical.full_column_design_pass)
        self.assertIn("NOT_CODE_ACCEPTANCE",obs.status)
        self.assertFalse(result.full_column_design_pass)

    def test_strict_json_html_share_same_unmodified_result(self):
        result=check_column(self.request)
        a=column_payload(result)
        b=json.loads(column_json(result))
        self.assertEqual(a,b)
        self.assertEqual(a,column_payload(result))
        self.assertNotIn("NaN",column_json(result))
        self.assertNotIn("Infinity",column_json(result))
        self.assertIn("NOT_EVALUATED",column_html(result))
        self.assertEqual(len(a["pmm_numerical_observations"]),1)

    def test_stale_trial_rejected_before_evaluation(self):
        stale=replace(self.trial,ref=RevisionRef("trial","t","r2"))
        with self.assertRaises(ValueError):
            replace(self.request,trial=stale)

    def test_missing_signed_source_never_assumed_zero(self):
        old=self.request.demand_problem.first_order
        empty=replace(old,population=replace(old.population,supplied=()))
        d=replace(self.request.demand_problem,first_order=empty)
        result=check_column(replace(self.request,demand_problem=d))
        self.assertEqual(len(result.demands.first_order.records),0)
        self.assertEqual(len(result.assessment.observations),0)
        self.assertFalse(result.full_column_design_pass)

    def test_envelope_cannot_supply_concurrent_second_order_action(self):
        row=self.fx.problem.population.supplied[0]
        changed=replace(self.key,step=replace(self.key.step,kind=StepKind.ENVELOPE_MAX))
        branch=EffectBranchKey(changed,EffectScale.LOCAL_P_DELTA,BendingAxis.LOCAL_2,self.rule)
        with self.assertRaises(ValueError):
            SourceEffectAction(branch,row.action,row.source_frame,"run1","gen1",row.evidence)

    def test_declared_code_rule_is_not_approval_receipt(self):
        replacement=RuleRef("TS500","2000","UNVERIFIED_TEST_RULE")
        checks=tuple(replace(c,rule=replacement) for c in self.request.required_checks)
        result=check_column(replace(self.request,required_checks=checks))
        self.assertFalse(result.full_column_design_pass)
        self.assertTrue(all(c.compliance.value=="NOT_EVALUATED"
                            for c in result.assessment.checks))

    def test_result_full_design_approval_cannot_be_forged(self):
        result=check_column(self.request)
        with self.assertRaises(ValueError):
            replace(result,full_column_design_pass=True)
        with self.assertRaises(ValueError):
            replace(result.assessment,full_column_pass=True)
