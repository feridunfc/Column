"""Read-only deterministic JSON and HTML projections of one section result."""
from __future__ import annotations
import json
from html import escape
from ..domain.section_requests import SectionCapacityResult


def section_payload(result: SectionCapacityResult)->dict:
    if type(result) is not SectionCapacityResult:
        raise TypeError("SectionCapacityResult required")
    requested=result.requested_policy
    applied=result.applied_policy
    def policy(p):
        return {
            "geometric_tolerance_mm":p.geometric_tol.as_mm,
            "axis_tolerance":p.axis_tol,
            "axial_balance_tolerance_n":p.force_balance_tol.as_n,
            "moment_tolerance_nmm":p.moment_tol.as_nmm,
            "relative_tolerance":p.relative_tol,
            "angle_count":p.angle_count,
            "max_iterations":p.max_iterations,
        }
    return {
        "schema":"column.section.numeric.v1.3-b1",
        "section_input":json.loads(result.input_trace.canonical_json),
        "section_input_sha256":result.input_trace.sha256,
        "section_input_fingerprint_scope":"DECLARED_SECTION_ONLY_NOT_AUTHENTICATION",
        "section_ref":{"namespace":result.section_ref.namespace,
                       "id":result.section_ref.identifier,
                       "revision":result.section_ref.revision},
        "material_revision":result.material_revision.revision,
        "frame_model":{
            "reference":result.frame_model_contract.reference,
            "axial_sign":result.frame_model_contract.axial_sign.value,
            "origin_mm":list(result.frame_model_contract.frame.origin.mm),
            "e1":list(result.frame_model_contract.frame.e1),
            "e2":list(result.frame_model_contract.frame.e2),
            "e3":list(result.frame_model_contract.frame.e3),
            "basis_max_residual":result.frame_basis_max_residual,
            "requested_axis_tolerance":result.requested_policy.axis_tol,
        },
        "request":result.request_kind,
        "status":result.status.value,
        "states":[{
            "angle_deg":s.normal_angle.as_deg,
            "c_mm":s.c.as_mm,
            "n_n":s.n.as_n,
            "m2_nmm":s.m2.as_nmm,
            "m3_nmm":s.m3.as_nmm,
            "axial_residual_n":None if s.axial_residual is None else s.axial_residual.as_n,
            "sampled_root_brackets":s.sampled_root_brackets,
            "root_scan_samples":s.root_scan_samples,
            "root_min_abs_residual_n":None if s.root_min_abs_residual is None else s.root_min_abs_residual.as_n,
        } for s in result.states],
        "radial_capacity_nmm":None if result.radial_capacity is None else result.radial_capacity.as_nmm,
        "radial_boundary_m2_nmm":None if result.radial_boundary_m2 is None else result.radial_boundary_m2.as_nmm,
        "radial_boundary_m3_nmm":None if result.radial_boundary_m3 is None else result.radial_boundary_m3.as_nmm,
        "angle_step_deg":None if result.angle_step is None else result.angle_step.as_deg,
        "angular_coverage":None if result.angular_coverage is None else {
            "attempted_count":result.angular_coverage.attempted_count,
            "resolved_indices":list(result.angular_coverage.resolved_indices),
            "missing_indices":list(result.angular_coverage.missing_indices),
            "complete":result.angular_coverage.is_complete,
        },
        "issues":list(result.issues),
        "numeric_root_quality":result.root_quality,
        "requested_policy":policy(requested),
        "applied_policy":policy(applied),
        "geometry":[{"name":n,"value":v,"unit":u} for n,v,u in result.source_geometry],
        "input_refs":[{
            "evidence_id":item.evidence_id,
            "producer":item.source.producer,
            "source_identifier":item.source.source_identifier,
            "source_record":item.source.record_identifier,
            "declared_units":item.source.declared_units,
            "acquisition_ref":item.source.acquisition_ref,
            "input_namespace":item.input_revision.namespace,
            "input_identifier":item.input_revision.identifier,
            "input_revision":item.input_revision.revision,
        } for item in result.input_refs],
        "law_ref":result.law_ref,
        "kernel_ref":result.kernel_ref,
        "full_column_design_pass":False,
        "outside_scope":["slenderness","second_order","shear","confinement","joint",
                         "reinforcement_design","full_column_code_compliance"],
    }


def section_report_json(result: SectionCapacityResult)->str:
    return json.dumps(section_payload(result),sort_keys=True,
                      ensure_ascii=False,allow_nan=False,separators=(",",":"))


def section_report_html(result: SectionCapacityResult)->str:
    """One pass through the SAME passive payload; no numerical kernel calls."""
    data=section_payload(result)
    def cell(x):
        if x is None:return "—"
        return escape(str(x))
    lines=[
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<title>RC section numerical result — not column approval</title></head><body>",
        "<h1>RC section numerical result</h1>",
        "<p>Not a TS500/TBDY full-column design PASS.</p>",
        "<dl>",
    ]
    for k in ("schema","request","status","law_ref","kernel_ref","numeric_root_quality"):
        lines.append(f"<dt>{cell(k)}</dt><dd>{cell(data[k])}</dd>")
    lines.append("</dl><h2>Local reference frame (declared, not transformed)</h2><dl>")
    for key,value in data["frame_model"].items():
        lines.append(f"<dt>{cell(key)}</dt><dd>{cell(value)}</dd>")
    snapshot=data["section_input"]
    mat=snapshot["material"]
    concrete=mat["concrete"]
    cage=snapshot["longitudinal"]
    lines.append("</dl><h2>Actual declared section / input fingerprint</h2>")
    lines.append(f"<p>SHA-256: {cell(data['section_input_sha256'])} "
                 f"({cell(data['section_input_fingerprint_scope'])})</p>")
    lines.append(f"<p>Section revision: {cell(snapshot['section_ref'])}; "
                 f"Material revision: {cell(mat['revision'])}; "
                 f"Layout revision: {cell(cage['revision'])}</p>")
    lines.append("<h3>Material model — declared design parameters</h3><dl>")
    for name in ("fck_mpa","fcd_mpa","k1","epsilon_cu"):
        lines.append(f"<dt>{cell(name)}</dt><dd>{cell(concrete[name])}</dd>")
    lines.append(f"<dt>TS500 rule</dt><dd>{cell(mat['rule'])}</dd>")
    for law in mat["steel_laws"]:
        lines.append(f"<p>Steel {cell(law['steel_ref'])}: "
                     f"fyd={cell(law['fyd_mpa'])} MPa; "
                     f"Es={cell(law['es_mpa'])} MPa; "
                     f"revision={cell(law['revision'])}</p>")
    lines.append("</dl><h3>Supplied longitudinal bars (section local 2/3)</h3>")
    lines.append(f"<p>Clear cover={cell(cage['clear_cover_mm'])} mm; "
                 f"tie diameter={cell(cage['tie_diameter_mm'])} mm</p>")
    lines.append("<table><tr><th>Bar ID</th><th>x2 [mm]</th>"
                 "<th>x3 [mm]</th><th>Diameter [mm]</th><th>Steel ref</th></tr>")
    for bar in cage["bars"]:
        lines.append("<tr>"+"".join(
            f"<td>{cell(bar[key])}</td>"
            for key in ("bar_id","x2_mm","x3_mm","diameter_mm","steel_ref")
        )+"</tr>")
    lines.append("</table><h2>Input section</h2><table>")
    for item in data["geometry"]:
        lines.append(f"<tr><th>{cell(item['name'])}</th><td>{cell(item['value'])}</td><td>{cell(item['unit'])}</td></tr>")
    lines.append("</table><h2>Numerical states</h2><table>")
    cols=("angle_deg","c_mm","n_n","m2_nmm","m3_nmm","axial_residual_n","sampled_root_brackets","root_scan_samples","root_min_abs_residual_n")
    lines.append("<tr>"+"".join(f"<th>{cell(k)}</th>" for k in cols)+"</tr>")
    for item in data["states"]:
        lines.append("<tr>"+"".join(f"<td>{cell(item[k])}</td>" for k in cols)+"</tr>")
    lines.append("</table><h2>Angular coverage</h2>")
    coverage=data["angular_coverage"]
    if coverage is None:
        lines.append("<p>NOT APPLICABLE — no angular envelope sampled</p>")
    else:
        lines.append(f"<p>Attempted: {cell(coverage['attempted_count'])}; Resolved: "
                     f"{cell(len(coverage['resolved_indices']))}; Missing: "
                     f"{cell(coverage['missing_indices'])}; Complete: "
                     f"{cell(coverage['complete'])}</p>")
    lines.append("<h2>Policies</h2>")
    for key in ("requested_policy","applied_policy"):
        lines.append(f"<h3>{cell(key)}</h3><dl>")
        for k,v in data[key].items():
            lines.append(f"<dt>{cell(k)}</dt><dd>{cell(v)}</dd>")
        lines.append("</dl>")
    lines.append("<h2>Radial result</h2>")
    for k in ("radial_capacity_nmm","radial_boundary_m2_nmm","radial_boundary_m3_nmm","angle_step_deg"):
        lines.append(f"<p>{cell(k)}: {cell(data[k])}</p>")
    lines.append("<h2>Issues and scope</h2><ul>")
    for issue in data["issues"]:
        lines.append(f"<li>{cell(issue)}</li>")
    for out in data["outside_scope"]:
        lines.append(f"<li>NOT EVALUATED: {cell(out)}</li>")
    lines.append("</ul><h2>Evidence</h2>")
    lines.append(f"<p>Section: {cell(data['section_ref'])}; Material revision: "
                 f"{cell(data['material_revision'])}</p>")
    for item in data["input_refs"]:
        for key in ("evidence_id","producer","source_identifier","source_record",
                    "declared_units","acquisition_ref","input_namespace",
                    "input_identifier","input_revision"):
            lines.append(f"<p>{cell(key)}: {cell(item[key])}</p>")
    lines.append("</body></html>")
    return "\n".join(lines)
