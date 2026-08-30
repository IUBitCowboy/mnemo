"""Report formatting for ICEX Submission Checker (FR-8, FR-9)."""


class Assessment:
    """Everything the report needs: submission identity, PR details, findings.

    v1.1 fields (V1-3/V1-4) are optional and backward compatible:
    is_late, ag_max_points, handgrading_points, ag_score, canvas_points.
    """

    def __init__(
        self,
        assignment,
        course,
        semester,
        student_name,
        pr_url,
        timestamp,
        tool_version,
        pr_details,
        findings,
        save_json_path=None,
        is_late=False,
        ag_max_points=None,
        handgrading_points=0,
        ag_score=None,
        canvas_points=None,
    ):
        self.assignment = assignment
        self.course = course
        self.semester = semester
        self.student_name = student_name
        self.pr_url = pr_url
        self.timestamp = timestamp
        self.tool_version = tool_version
        self.pr_details = pr_details
        self.findings = findings
        self.save_json_path = save_json_path
        self.is_late = is_late
        self.ag_max_points = ag_max_points
        self.handgrading_points = handgrading_points
        self.ag_score = ag_score
        self.canvas_points = canvas_points


def summarize_findings(findings):
    """Count assessments and sum points (FR-8 summary)."""
    counts = {"pass": 0, "partial": 0, "fail": 0, "needs-review": 0}
    total = 0
    recommended = 0
    for f in findings:
        counts[f.assessment] = counts.get(f.assessment, 0) + 1
        total += f.points_max
        if f.points_recommended is not None:
            recommended += f.points_recommended
    return {
        "pass": counts["pass"],
        "partial": counts["partial"],
        "fail": counts["fail"],
        "needs-review": counts["needs-review"],
        "total_points": total,
        "recommended_points": recommended,
    }


def build_text_report(assessment):
    """Human-readable report to stdout (FR-8)."""
    s = summarize_findings(assessment.findings)
    lines = []
    lines.append("=" * 72)
    lines.append("ICEX SUBMISSION CHECKER REPORT")
    lines.append("=" * 72)
    lines.append("Assignment: %s (%s %s)" % (assessment.assignment, assessment.course, assessment.semester))
    lines.append("Student:    %s" % (assessment.student_name or "(not parsed from title)"))
    lines.append("PR URL:     %s" % assessment.pr_url)
    lines.append("Assessed:   %s" % assessment.timestamp)
    lines.append("Tool:       icex_checker %s" % assessment.tool_version)
    if assessment.is_late:
        lines.append("")
        lines.append("*** LATE SUBMISSION — handgrading zeroed per course policy ***")
    lines.append("")

    lines.append("SUMMARY")
    lines.append("-" * 72)
    lines.append("Total points possible: %s" % s["total_points"])
    lines.append("Recommended points:     %s" % s["recommended_points"])
    lines.append("passed: %d | partial: %d | failed: %d | needs-review: %d"
                 % (s["pass"], s["partial"], s["fail"], s["needs-review"]))
    lines.append("")

    lines.append("CRITERIA")
    lines.append("-" * 72)
    for f in assessment.findings:
        lines.append("[%s] %s (max %s, recommended %s)"
                     % (f.assessment.upper(), f.criterion_name, f.points_max,
                        f.points_recommended if f.points_recommended is not None else "n/a"))
        for ev in f.evidence:
            lines.append("    evidence: %s" % ev)
        if f.notes:
            lines.append("    note: %s" % f.notes)
        lines.append("")

    lines.append("PR DETAILS")
    lines.append("-" * 72)
    pd = assessment.pr_details or {}
    lines.append("Title:       %s" % pd.get("title", ""))
    lines.append("Description: %s" % _truncate(pd.get("description", ""), 200))
    lines.append("Branches:    %s -> %s" % (pd.get("head_ref", ""), pd.get("base_ref", "")))
    lines.append("Commits:     %s" % pd.get("commits", ""))
    if pd.get("merged"):
        lines.append("State:       merged")
    else:
        lines.append("State:       %s" % pd.get("state", ""))
    lines.append("")

    if assessment.ag_max_points is not None:
        lines.append("AG SCORE")
        lines.append("-" * 72)
        max_pts = assessment.ag_max_points
        hg_max = assessment.handgrading_points or 0
        if assessment.ag_score is not None:
            lines.append("AG score: %s/%s" % (assessment.ag_score, max_pts))
        else:
            lines.append("AG score: (not entered — TA enters from AG platform)")
        if hg_max > 0:
            if assessment.is_late:
                lines.append("Handgrading: 0/%s (LATE submission — zeroed per policy)" % hg_max)
            else:
                lines.append(
                    "Handgrading: (TA enters 0-%s from AG handgrader)" % hg_max
                )
        # The tool only knows the AG score in v1.1 (handgrading is entered
        # manually in the AG platform). Scaling therefore uses the AG score
        # alone and notes that handgrading completes the total.
        ag_total = assessment.ag_score or 0
        if assessment.ag_score is not None:
            scale_denom = max_pts + hg_max
            lines.append("AG-scale total so far: %s/%s (final = + handgrading%s)"
                         % (ag_total, scale_denom, " = 0" if assessment.is_late else " 0-%s" % hg_max))
        if assessment.canvas_points is not None and assessment.canvas_points != max_pts + hg_max:
            scale_denom = max_pts + hg_max
            scaled = (ag_total / scale_denom) * assessment.canvas_points if scale_denom else 0.0
            lines.append("Canvas score (scaled to %s, handgrading pending): %.1f/%s"
                         % (assessment.canvas_points, scaled, assessment.canvas_points))
        lines.append("")

    lines.append("TA ACTION ITEMS")
    lines.append("-" * 72)
    action_items = []
    for f in assessment.findings:
        if f.assessment == "needs-review":
            action_items.append(
                "  [ ] Review manually: %s — %s" % (f.criterion_name, f.notes or "see PR")
            )
        elif f.ta_confirm:
            action_items.append(
                "  [ ] Confirm: %s — %s" % (f.criterion_name, f.notes or "see PR")
            )
    if assessment.ag_max_points is not None:
        action_items.append(
            "  [ ] Check Canvas gradebook for prior submissions. If this is a "
            "resubmission, do not overwrite the prior handgrading score; "
            "enter the updated AG score in Canvas."
        )
    if action_items:
        lines.extend(action_items)
    else:
        lines.append("  (none — all criteria mechanically verified)")
    lines.append("")
    lines.append("PR for direct access: %s" % assessment.pr_url)
    if assessment.save_json_path:
        lines.append("Full JSON saved to: %s" % assessment.save_json_path)
    lines.append("=" * 72)
    return "\n".join(lines)


def build_json_report(assessment):
    """Machine-readable assessment dict (FR-9)."""
    return {
        "tool": "icex_checker",
        "tool_version": assessment.tool_version,
        "assignment": assessment.assignment,
        "course": assessment.course,
        "semester": assessment.semester,
        "student_name": assessment.student_name,
        "pr_url": assessment.pr_url,
        "assessed_at": assessment.timestamp,
        "pr_details": assessment.pr_details or {},
        "summary": summarize_findings(assessment.findings),
        "is_late": assessment.is_late,
        "ag_max_points": assessment.ag_max_points,
        "handgrading_points": assessment.handgrading_points,
        "ag_score": assessment.ag_score,
        "canvas_points": assessment.canvas_points,
        "criteria": [
            {
                "name": f.criterion_name,
                "checker": f.checker,
                "points_max": f.points_max,
                "assessment": f.assessment,
                "points_recommended": f.points_recommended,
                "evidence": f.evidence,
                "notes": f.notes,
                "ta_confirm": f.ta_confirm,
            }
            for f in assessment.findings
        ],
    }


def _truncate(text, limit):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"
