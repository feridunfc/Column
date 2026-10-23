"""C6 read-only strict projections from one immutable ColumnResult.

No engineering recomputation in JSON/HTML. A display of a successful
software flow is NOT a completed TS500/TBDY member code assessment.
"""
from __future__ import annotations
import json
from html import escape
from ..application.column_check import ColumnResult


def column_payload(result:ColumnResult)->dict:
    if type(result) is not ColumnResult:
        raise TypeError("ColumnResult only")
    ref=lambda r: {"namespace":r.namespace,"identifier":r.identifier,"revision":r.revision}
    return {
      "schema":"column.check.draft.v1",
      "release_status":"C02_NOT_RATIFIED_SUPERVISOR_PENDING",
      "scenario":ref(result.scenario_ref),
      "trial":ref(result.trial_ref),
      "physical_member":ref(result.member_ref),
      "candidate":ref(result.candidate_ref),
      "outcome":result.outcome,
      "full_column_design_pass":result.full_column_design_pass,
      "eligibility":result.assessment.eligibility.value,
      "is_complete":result.assessment.is_complete,
      "has_failures":result.assessment.has_failures,
      "observed_utilization_exceeds_unity":any(
        x.radial_utilization_observed is not None and x.radial_utilization_observed>1.0
        for x in result.assessment.observations),
      "geometry":{
        "bottom_mm":list(result.geometry.bottom.mm),
        "top_mm":list(result.geometry.top.mm),
        "bottom_face_id":result.geometry.bottom_face_id,
        "top_face_id":result.geometry.top_face_id,
        "centreline_mm":result.geometry.centreline.as_mm,
        "declared_lengths":[
          {"kind":x.kind.value,"mm":x.value.as_mm,
           "source_evidence":x.evidence.evidence_id,
           "method":None if x.method is None else {
             "code":x.method.code_id,"edition":x.method.edition,
             "rule":x.method.rule_id}}
          for x in result.geometry.supplied_lengths],
        "missing_lengths":[x.value for x in result.geometry.missing_length_kinds],
        "stiffness_ready":result.geometry.stiffness_ready,
        "second_order_ready":result.geometry.second_order_ready,
      },
      "mechanics":{
        "status":result.mechanics.status,
        "second_order_computed":result.mechanics.second_order_computed,
        "EI_declared_axes":[x.axis.value for x in result.mechanics.stiffness.declarations],
        "EI_missing_axes":[x.value for x in result.mechanics.stiffness.missing_axes],
        "story_directions":[x.direction.value for x in result.mechanics.story],
        "missing_second_order":[
          {"scale":s.value,"direction":a.value} for s,a in result.mechanics.missing_effects],
        "issues":list(result.mechanics.issues),
      },
      "demands":{
        "status":result.demands.status.value,
        "first_order_status":result.demands.first_order.status.value,
        "expected_count":len(result.demands.first_order.expected_keys),
        "signed_first_order_count":len(result.demands.first_order.records),
        "missing_count":len(result.demands.first_order.missing_keys),
        "missing_keys":[repr(k) for k in result.demands.first_order.missing_keys],
        "source_evidence_refs":list(result.demands.first_order.matched_qualification_evidence),
        "effects_unapproved":not result.demands.second_order_approved,
        "declared_effect_count":len(result.demands.effects),
      },
      "pmm_numerical_observations":[{
        "source_key":repr(x.source_key),
        "section_status":x.numerical.status.value,
        "radial_capacity_nmm":None if x.numerical.radial_capacity is None else x.numerical.radial_capacity.as_nmm,
        "sampled_utilization_not_code_compliance":x.radial_utilization_observed,
        "angle_count":x.numerical.applied_policy.angle_count,
        "issues":list(x.numerical.issues),
        "meaning":x.status,
      } for x in result.assessment.observations],
      "checks":[{
        "check_id":c.check_id,
        "applicability":c.applicability.value,
        "execution":c.execution.value,
        "compliance":c.compliance.value,
        "freshness":c.freshness.value,
        "expected_keys":list(c.coverage.expected_keys),
        "completed_keys":list(c.coverage.completed_keys),
        "reason":c.reason,
        "rule":{"code":c.rule.code_id,"edition":c.rule.edition,"rule":c.rule.rule_id},
      } for c in result.assessment.checks],
      "unresolved_scope":list(result.assessment.missing_scopes),
      "issues":list(result.issues),
    }


def column_json(result:ColumnResult)->str:
    return json.dumps(column_payload(result),sort_keys=True,allow_nan=False,
                      ensure_ascii=False,separators=(",",":"))


def column_html(result:ColumnResult)->str:
    payload=column_payload(result)
    # HTML only projects payload fields, no calculations.
    rows="".join(
        "<tr><td>"+escape(c["check_id"])+"</td><td>"+
        escape(c["execution"])+"</td><td>"+
        escape(c["compliance"])+"</td><td>"+
        escape(c["reason"])+"</td></tr>"
        for c in payload["checks"]
    )
    return (
      '<!doctype html><html lang="tr"><meta charset="utf-8"><title>Column Draft</title>'
      '<body><h1>Column — C Taslak İnceleme</h1><p>Release: '+
      escape(payload["release_status"])+'</p><p>Result: '+
      escape(payload["outcome"])+'</p><p>Member: '+
      escape(payload["physical_member"]["identifier"])+'</p>'
      '<table><thead><tr><th>Kontrol</th><th>İcra</th><th>Uygunluk</th>'
      '<th>Açıklama</th></tr></thead><tbody>'+rows+'</tbody></table>'
      '<h2>Açık sorunlar</h2><ul>'+
      "".join("<li>"+escape(x)+"</li>" for x in payload["issues"])+
      '</ul><p>Eksik yöntem/kapsam için uygunluk kararı verilmemiştir.</p></body></html>'
    )
