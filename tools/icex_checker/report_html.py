"""TA-facing HTML report emitter (FA26 workflow change, 2026-11-13).

Batch mode keeps its classic .txt/.json outputs; this module turns the
same assessments into a static HTML bundle Kurt's TAs open from the
OneDrive share:

    submissions/report.html                     — shared index, one page
    submissions/TA-reports/<lane>/<netid>.html  — one page per submission
    submissions/TA-reports/<lane>/manifest.json — lane facts for rebuilds

Design rulings baked in:
- One shared index page; team/TA filtering via tiny inline JS (TAs open
  with the OneDrive sync client, so scripts run; content still degrades
  to plain static text).
- Re-runs overwrite in place; every page and section shows the run
  timestamp.
- Absence is first-class: exception rows (file present, tool failed)
  and MISSING rows (no Canvas submission file at all) are rendered next
  to the graded entries, so a TA sees a gap at a glance.
- Team lanes show the TAP Collaboration Coefficient: per-student
  recommendation = team recommendation x coefficient, ~50% floor,
  coefficient defaults to 100% and the TA adjusts per peer eval.
- Every page states RECOMMENDED, NOT FINAL — the TA enters gradebook
  scores and comments.
"""

import html
import json
import pathlib
import re
from datetime import datetime

_CSS = """
:root { --fg:#1c1b1f; --mut:#63616c; --line:#e2e0e8; --card:#fff; }
* { box-sizing:border-box; }
body { font:15px/1.55 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
       color:var(--fg); background:#faf9fc; margin:0; padding:24px; }
main { max-width:1120px; margin:0 auto; }
h1 { font-size:22px; margin:0 0 4px; }
h2 { font-size:18px; margin:6px 0 6px; }
h3 { font-size:14px; margin:14px 0 6px; color:#b3261e; }
.mut,.small { color:var(--mut); } .small { font-size:12.5px; }
.banner { background:#fff8e1; border:2px solid #e7b416; border-radius:10px;
          padding:10px 14px; margin:12px 0 18px; font-weight:600; }
.card { background:var(--card); border:1px solid var(--line);
        border-radius:10px; padding:12px 16px; margin:12px 0; }
table { border-collapse:collapse; width:100%; margin:8px 0; }
th,td { text-align:left; padding:6px 10px; border-bottom:1px solid
        var(--line); vertical-align:top; font-size:14px; }
th { color:var(--mut); font-weight:600; font-size:12px;
     text-transform:uppercase; letter-spacing:.03em; }
.b { display:inline-block; padding:1px 8px; border-radius:99px;
     font-size:11.5px; font-weight:700; color:#fff; white-space:nowrap; }
.b.ok { background:#1a7f4b; } .b.fail { background:#b3261e; }
.b.part { background:#8a6d00; } .b.review { background:#5c3bd6; }
.b.missing { background:#b3261e; } .b.late { background:#8a6d00; }
a { color:#0b57d0; }
.chips { display:flex; flex-wrap:wrap; gap:6px; margin:8px 0 16px; }
.chip { border:1px solid var(--line); background:var(--card);
        border-radius:99px; padding:3px 12px; font-size:13.5px; }
.chip.on { background:#1e293b; color:#fff; border-color:#1e293b; }
.hide { display:none !important; }
.warnrow td { background:#fff8e1; }
.lane-sec.hide { display:none; }
.scorebox { display:flex; gap:22px; align-items:baseline; flex-wrap:wrap; }
.scorebox .big { font-size:34px; font-weight:800; line-height:1; }
.scorebox .lbl { color:var(--mut); font-size:11.5px;
                 text-transform:uppercase; letter-spacing:.04em; }
details.lane { margin:6px 0; border:1px solid var(--line);
               border-radius:10px; background:var(--card); }
details.lane summary { cursor:pointer; padding:10px 14px;
        font-weight:650; display:flex; flex-wrap:wrap; gap:6px;
        align-items:baseline; border-radius:10px; }
details.lane summary:hover { background:#f2f0f7; }
details.lane[open] summary { border-bottom:1px solid var(--line); }
details.lane > *:not(summary) { padding:4px 14px 10px; }
details.lane h3 { margin:12px 0 4px; }
.week-h { margin:22px 0 6px; font-size:16px; color:var(--mut);
          text-transform:uppercase; letter-spacing:.05em;
          border-bottom:2px solid var(--line); padding-bottom:4px; }
.links a { margin-right:14px; }
details { margin:6px 0; border:1px solid var(--line); border-radius:8px;
          padding:6px 10px; background:#fff; }
details summary { cursor:pointer; font-weight:600; font-size:13px; }
details div { margin:6px 0 2px; color:var(--mut); font-size:13px;
              white-space:pre-wrap; }
button { font:inherit; cursor:pointer; border-radius:8px;
         border:1px solid var(--line); background:#fff; padding:2px 8px;
         font-size:12px; }
footer { margin-top:24px; color:var(--mut); font-size:12px;
         border-top:1px solid var(--line); padding-top:10px; }
@media print { .chips,button { display:none; } }
"""

_JS = """
function select(btn){
 document.querySelectorAll('.chip').forEach(b=>b.classList.toggle(
   'on', b===btn));
 apply();
}
function chip(btn){
 if(btn.classList.contains('on') && btn.dataset.team!=='*'){
   select(null);            // deselect -> nothing picked -> all
 } else { select(btn); }
}
function apply(){
 const chosen=[];
 document.querySelectorAll('.chip.on').forEach(b=>chosen.push(
   b.dataset.team));
 const filtered = chosen.length>0 && chosen.indexOf('*')<0;
 document.querySelectorAll('[data-team]').forEach(el=>{
  if(el.classList.contains('chip'))return;
  el.classList.toggle('hide', filtered&&chosen.indexOf(el.dataset.team)<0);});
 document.querySelectorAll('details.lane').forEach(d=>{
  let vis=0;
  d.querySelectorAll('[data-team]').forEach(r=>{
   if(!r.classList.contains('hide'))vis++;});
  d.open = filtered ? vis>0 : false;
 });
}
function copyable(btn){const t=btn.getAttribute('data-text');
 navigator.clipboard.writeText(t).then(()=>{btn.textContent='copied';
 setTimeout(()=>{btn.textContent='copy comment';},1200);});}
"""

_BADGE = {
    "pass": '<span class="b ok">pass</span>',
    "partial": '<span class="b part">partial</span>',
    "fail": '<span class="b fail">fail</span>',
    "needs-review": '<span class="b review">needs review</span>',
}


def _esc(s):
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def _esc_url(u):
    return _esc(u)


def now_ts():
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")


def _submitter_from_filename(filename):
    return filename.split("_")[0]


def _canonical_username(roster_obj, raw):
    if not raw or roster_obj is None:
        return raw or ""
    try:
        return roster_obj.canonical_username(raw) or raw
    except Exception:
        return raw


def _collect_roster_view(csv_path=None, roster_obj=None):
    """team -> {ta, members: [{iu, canvas_name, name, id}]}.

    Prefers the raw roster CSV (Team,TA,IU Username,Canvas Name,Name,ID)
    since it carries the Canvas IDs and names the TA view needs; falls
    back to the Roster object (usernames + TA only).
    """
    view = {}
    if csv_path:
        try:
            import csv as _csv
            with open(csv_path, newline="", encoding="utf-8-sig") as fh:
                for r in _csv.DictReader(fh):
                    team = (r.get("Team") or "").strip()
                    if not team:
                        continue
                    entry = view.setdefault(
                        team, {"ta": "", "members": []})
                    if (r.get("TA") or "").strip():
                        entry["ta"] = r["TA"].strip()
                    entry["members"].append({
                        "iu": (r.get("IU Username") or "").strip(),
                        "canvas_name": (r.get("Canvas Name") or "").strip(),
                        "name": (r.get("Name") or r.get("Canvas Name")
                                 or "").strip(),
                        "id": str((r.get("ID") or "").strip()),
                        "section": (r.get("Section") or "").strip(),
                    })
            if view:
                return view
        except (OSError, KeyError):
            pass
    if roster_obj is None:
        return view
    for team_id in sorted(getattr(roster_obj, "_teams", {}) or {}):
        ta = ""
        try:
            ta = roster_obj.ta_for_team(team_id) or ""
        except Exception:
            ta = ""
        entry = view.setdefault(team_id, {"ta": ta, "members": []})
        for iu in roster_obj.members(team_id):
            entry["members"].append({
                "iu": iu, "canvas_name": "", "name": iu, "id": "",
            })
    return view


def _roster_team_of(roster_view, netid):
    for team, info in roster_view.items():
        for m in info["members"]:
            if m["iu"] == netid:
                return team
    return ""


def _roster_row_of(roster_view, netid):
    for team, info in roster_view.items():
        for m in info["members"]:
            if m["iu"] == netid:
                return m
    return None


def _assignment_title(batch_dir, first_result):
    # Canvas export titles carry the week + full assignment name — the
    # friendliest label TAs know. Fall back to the rubric assignment
    # code, then the lane slug.
    try:
        head = (batch_dir / first_result["file"]).read_text(
            errors="replace")[:2048]
        m = re.search(r"<title>(.*?)</title>", head, re.S)
        if m:
            return re.sub(r":\s+[^:]+$", "", m.group(1).strip())
    except OSError:
        pass
    a = first_result.get("_assessment")
    if a is not None and getattr(a, "assignment", None):
        return a.assignment
    return batch_dir.name.replace("_", " ")


# ---------------------------------------------------------------------------
# Lane emission
# ---------------------------------------------------------------------------


def emit_lane(batch_dir, results, out_root, run_ts, rubric, roster_obj,
              lanes_dir=None, filtered_teams=None, roster_csv=None):
    """Write one lane's pages + manifest, then rebuild the shared index.

    filtered_teams: when the batch ran with --teams, only those teams
    were processed — restrict MISSING/gap detection to them so unrun
    teams don't appear as absences. roster_csv: path to the raw roster
    CSV (preferred member source — carries Canvas IDs and names).
    """
    out_root = pathlib.Path(out_root)
    lane_slug = batch_dir.name
    lane_dir = pathlib.Path(
        lanes_dir or (out_root / "TA-reports" / lane_slug))
    lane_dir.mkdir(parents=True, exist_ok=True)

    roster_view = _collect_roster_view(csv_path=roster_csv,
                                       roster_obj=roster_obj)
    coeff_default = getattr(rubric, "collaboration_coefficient", None) or 1.0
    is_team = (getattr(rubric, "type", "") == "team"
               or getattr(rubric, "ownership_check", "") == "team"
               or "team_pr" in lane_slug)

    processed = [r for r in results if r.get("status") == "processed"
                 and r.get("_assessment") is not None]
    failed = [r for r in results if r.get("status") == "failed"]
    title = (_assignment_title(batch_dir, processed[0])
             if processed else lane_slug.replace("_", " "))

    submitter_teams = {}   # netid -> team
    team_reporters = {}    # team -> set(netid)
    entries = []
    for r in processed:
        a = r["_assessment"]
        netid = _canonical_username(
            roster_obj, _submitter_from_filename(r["file"]))
        team = r.get("team") or _roster_team_of(roster_view, netid)
        row = _roster_row_of(roster_view, netid) or {}
        page_name = re.sub(r"[^A-Za-z0-9._-]", "-",
                           "%s.html" % (netid or "unknown"))
        _write_report_page(
            lane_dir / page_name, a, run_ts, rubric,
            team=team, ta=(roster_view.get(team, {}) or {}).get("ta", ""),
            roster_row=row, coeff_default=coeff_default,
            is_team=is_team, lane_title=title)
        entry = {
            "file": r["file"],
            "netid": netid or "",
            "name": row.get("name", "") or netid,
            "canvas_id": row.get("id", ""),
            "team": team or "",
            "ta": (roster_view.get(team, {}) or {}).get("ta", ""),
            "status": "processed",
            "recommended": r.get("recommended_points"),
            "total": r.get("total_points"),
            "is_late": bool(getattr(a, "is_late", False)),
            "pr_url": r.get("pr_url") or getattr(a, "pr_url", "") or "",
            "page": "TA-reports/%s/%s" % (lane_slug, page_name),
        }
        if netid:
            submitter_teams[netid] = team or ""
        team_reporters.setdefault(team or "(unclear)", set()).add(netid)
        entries.append(entry)

    exceptions = []
    for r in failed:
        netid = _canonical_username(
            roster_obj, _submitter_from_filename(r["file"]))
        exceptions.append({
            "file": r["file"],
            "netid": netid or "",
            "name": (_roster_row_of(roster_view, netid) or {}).get(
                "name", "") or netid or _submitter_from_filename(r["file"]),
            "team": _roster_team_of(roster_view, netid) or "",
            "error": str(r.get("error", ""))[:400],
        })

    seen_files = set()
    for f in batch_dir.glob("*.html"):
        seen_files.add(_canonical_username(
            roster_obj, _submitter_from_filename(f.name)))

    missing, member_gaps = [], []
    sections_expected = getattr(rubric, "expected_sections", None) or []

    def _in_scope(team):
        return (filtered_teams is None) or (team in filtered_teams)

    def _section_expected(m):
        if not sections_expected:
            return True
        sec = (m.get("section") or "").upper()
        return any(tok.upper() in sec for tok in sections_expected)

    if roster_view:
        if not is_team:
            for team in sorted(roster_view):
                if not _in_scope(team):
                    continue
                for m in roster_view[team]["members"]:
                    if m["iu"] not in seen_files and _section_expected(m):
                        missing.append({
                            "team": team, "iu": m["iu"],
                            "name": m["name"], "ta": roster_view[team]["ta"],
                        })
        else:
            for team in sorted(roster_view):
                if not _in_scope(team):
                    continue
                members = roster_view[team]["members"]
                has_reports = bool(team_reporters.get(team))
                has_exc = any(x["team"] == team for x in exceptions)
                if not has_reports:
                    if not has_exc:
                        missing.append({
                            "team": team, "iu": "(team)",
                            "name": team + " — no team submission found",
                            "ta": roster_view[team]["ta"],
                        })
                    continue
                exc_netids = {x["netid"] for x in exceptions
                              if x["team"] == team}
                for m in members:
                    if m["iu"] not in team_reporters[team] \
                            and m["iu"] not in exc_netids \
                            and m["iu"] not in seen_files:
                        member_gaps.append({
                            "team": team, "iu": m["iu"],
                            "name": m["name"],
                            "ta": roster_view[team]["ta"],
                        })

    manifest = {
        "tool": "icex_checker",
        "generated_for": "SE1 FA26 TA grading view",
        "lane": lane_slug,
        "assignment_title": title,
        "assignment_code": getattr(rubric, "assignment", ""),
        "type": "team" if is_team else "individual",
        "total_points": getattr(rubric, "total_points", None)
        or (processed[0].get("total_points") if processed else None),
        "canvas_points": getattr(rubric, "canvas_points", None),
        "collaboration_coefficient": coeff_default,
        "run_ts": run_ts,
        "lane_dir": "TA-reports/%s" % lane_slug,
        "entries": entries,
        "exceptions": exceptions,
        "missing": missing,
        "member_gaps": member_gaps,
        "teams": {t: {"ta": v["ta"]} for t, v in roster_view.items()},
    }
    cid_course = getattr(rubric, "canvas_course_id", None)
    cid_assign = getattr(rubric, "canvas_assignment_id", None)
    if cid_course and cid_assign:
        manifest["canvas_assignment_url"] = \
            "https://iu.instructure.com/courses/%s/assignments/%s" % (
                cid_course, cid_assign)
    for e in entries:
        sg = cs = ""
        if cid_course and cid_assign:
            sid = e.get("canvas_id") or ""
            sg = ("https://iu.instructure.com/courses/%s/gradebook/"
                  "speed_grader?assignment_id=%s&student_id=%s"
                  % (cid_course, cid_assign, sid))
            cs = ("https://iu.instructure.com/courses/%s/assignments/%s/"
                  "submissions/%s" % (cid_course, cid_assign, sid))
        e["speedgrader"] = sg
        e["canvas_submission"] = cs
    (lane_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    index_path = emit_index(out_root, run_ts)
    return manifest, index_path


# ---------------------------------------------------------------------------
# Per-submission page
# ---------------------------------------------------------------------------


def _write_report_page(path, a, run_ts, rubric, team="", ta="",
                       roster_row=None, coeff_default=1.0, is_team=False,
                       lane_title=""):
    findings = list(a.findings)
    rec = sum(f.points_recommended for f in findings
              if f.points_recommended is not None)
    total = sum(f.points_max for f in findings)
    netid = (roster_row or {}).get("iu", "") or a.student_name
    canvas_id = (roster_row or {}).get("id", "")
    email = ("%s@iu.edu" % netid) if netid and "@" not in str(netid) else ""

    links = []
    if a.pr_url:
        links.append('<a href="%s">GitHub submission &#8594;</a>'
                     % _esc_url(a.pr_url))
    cid_course = getattr(rubric, "canvas_course_id", None)
    cid_assign = getattr(rubric, "canvas_assignment_id", None)
    if cid_course and cid_assign and canvas_id:
        sid = _esc_url(canvas_id)
        links.append(
            '<a href="https://iu.instructure.com/courses/%s/gradebook/'
            'speed_grader?assignment_id=%s&amp;student_id=%s">'
            'Canvas SpeedGrader &#8594;</a>'
            % (_esc_url(cid_course), _esc_url(cid_assign), sid))
        links.append(
            '<a href="https://iu.instructure.com/courses/%s/assignments/'
            '%s/submissions/%s">Canvas submission &#8594;</a>'
            % (_esc_url(cid_course), _esc_url(cid_assign), sid))
    if email:
        links.append('<a href="mailto:%s">email %s</a>'
                     % (_esc_url(email), _esc(netid)))

    rows, confirms = [], []
    for f in findings:
        pts = ("—" if f.points_recommended is None
               else "%d / %d" % (f.points_recommended, f.points_max))
        rows.append(
            "<tr data-team=''><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (_esc(f.criterion_name),
               _BADGE.get(f.assessment, _esc(f.assessment)), pts))
        if f.ta_confirm:
            confirms.append(f)
        if f.evidence:
            rows.append(
                "<tr data-team=''><td colspan='3'><details>"
                "<summary>evidence (%d)</summary><div>%s</div></details>"
                "</td></tr>" % (len(f.evidence),
                                _esc("\n".join(f.evidence))))
        if f.notes:
            btn = ('<button data-text="%s" onclick="copyable(this)">'
                   "copy comment</button>" % _esc(f.notes))
            rows.append(
                "<tr data-team=''><td colspan='3'><em>%s</em> %s</td></tr>"
                % (_esc(f.notes), btn))

    confirm_html = ""
    if confirms:
        confirm_html = (
            "<div class='card'><strong>TA to-do — confirm before "
            "entering scores</strong><ul>%s</ul></div>" % "".join(
                "<li>%s — %s</li>" % (_esc(f.criterion_name),
                                      _esc(f.notes or ""))
                for f in confirms))

    coeff_html = ""
    if is_team and rec is not None:
        pct = int(round(coeff_default * 100))
        coeff_html = (
            "<div class='card'><strong>TAP Collaboration "
            "Coefficient:</strong> %d%% default (full pass-through of the "
            "team score). Per-student recommendation = team %d &times; "
            "each member's coefficient; the TA sets the coefficient per "
            "TAP peer evaluation before entering individual scores "
            "(floor &asymp; 50%%, Merit/Demerit &plusmn;20%%, "
            "team-initiated).</div>" % (pct, rec))

    who = (_esc("Team: %s · TA: %s%s" % (
        team or "—", ta or "—",
        " · Canvas ID: %s" % canvas_id if canvas_id else ""))
        if team else _esc("Course: %s · %s%s" % (
            a.course, a.semester,
            " · Canvas ID: %s" % canvas_id if canvas_id else "")))
    late = ' <span class="b late">LATE</span>' if a.is_late else ""
    links_html = ""
    if links:
        links_html = "<div class='card links'>%s</div>" % "".join(links)

    page = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>%s — %s</title>
<style>%s</style>
<script>%s</script>
</head><body><main>
<h1>%s <small class="mut">— %s%s</small></h1>
<div class="banner">RECOMMENDED, NOT FINAL &mdash; the TA reviews the work
via the links below, then enters the final score and comments in the
Canvas gradebook.</div>
<div class="card links"><span class="mut small">%s</span></div>
<div class="card scorebox">
 <div><div class="big">%d</div><div class="lbl">recommended</div></div>
 <div><div class="big" style="font-size:22px">%d</div>
 <div class="lbl">rubric total</div></div>
 <div><div class="lbl">%s</div></div>
</div>
%s%s
<table>
<tr><th>criterion</th><th>verdict</th><th>points</th></tr>
%s
</table>
<details><summary>full evidence log</summary><div>%s</div></details>
<footer>icex_checker · run %s · batch re-runs overwrite these pages
(timestamp = latest run) · team %s · TA %s</footer>
</main></body></html>""" % (
        _esc(lane_title), _esc(a.student_name),
        _CSS, _JS,
        _esc(lane_title), _esc(a.student_name), late,
        who, rec, total, who,
        links_html, confirm_html + coeff_html,
        "".join(rows),
        _esc("\n".join(e for f in findings for e in f.evidence)) or "—",
        _esc(run_ts), _esc(team or "—"), _esc(ta or "—"),
    )
    path.write_text(page)


# ---------------------------------------------------------------------------
# Shared index
# ---------------------------------------------------------------------------


def emit_index(out_root, run_ts):
    """Rebuild submissions/report.html: assignments grouped by week,
    each assignment a click-to-open card; absences visible at a glance
    (even while folded) via the red count badges on the summary row."""
    out_root = pathlib.Path(out_root)
    lanes = []
    for mf in sorted(out_root.glob("TA-reports/*/manifest.json")):
        try:
            lanes.append(json.loads(mf.read_text()))
        except (OSError, ValueError):
            continue
    if not lanes:
        return None

    teams = {}
    for lane in lanes:
        for t, info in lane.get("teams", {}).items():
            teams.setdefault(t, info.get("ta", ""))

    chips = ['<button class="chip on" data-team="*" onclick="chip(this)">'
             "<strong>All</strong></button>"]
    chips += ['<button class="chip" data-team="%s" onclick="chip(this)">'
              "%s</button>" % (_esc(t), _esc(t)) for t in sorted(teams)]

    # group lanes by the Week N in their Canvas export title
    grouped = {}
    for lane in lanes:
        m = re.search(r"Week (\d+)", lane.get("assignment_title") or "",
                      re.IGNORECASE)
        grouped.setdefault(int(m.group(1)) if m else 999,
                           []).append(lane)

    week_blocks = []
    for week in sorted(grouped):
        cards = []
        for lane in grouped[week]:
            entries = lane.get("entries", [])
            exc = lane.get("exceptions", [])
            missing = lane.get("missing", [])
            gaps = lane.get("member_gaps", [])
            coeff = lane.get("collaboration_coefficient") or 1.0
            is_team = lane.get("type") == "team"
            n_gap = len(exc) + len(missing) + len(gaps)
            gap_badges = (
                '<span class="b fail">%d exception</span>'
                % len(exc) if exc else "")
            badges = [
                '<span class="mut small">%d report%s</span>'
                % (len(entries), "s" if len(entries) != 1 else ""),
                gap_badges,
                ('<span class="b fail">%d MISSING</span>' % len(missing)
                 if missing else ""),
                ('<span class="b part">team &times;%g</span>' % coeff
                 if is_team else ""),
            ]
            canvas_link = ('<a href="%s">Canvas: assignment page &rarr;'
                           "</a>" % _esc_url(
                               lane["canvas_assignment_url"])
                           if lane.get("canvas_assignment_url") else "")

            cols = ("<tr><th>student</th><th>team</th><th>recommended</th>"
                    "<th>report &amp; links</th></tr>")
            rows = []
            for e in sorted(entries, key=lambda x: (x["team"] or "zz",
                                                    x["name"])):
                rec = e.get("recommended")
                if is_team and rec is not None:
                    adj = round(rec * coeff)
                    rec_html = ("<strong>%s</strong>/%s <span class='mut "
                                "small'>&times;%s &rarr; %s/student</span>"
                                % (rec, e.get("total", ""),
                                   ("%g" % coeff), adj))
                elif rec is not None:
                    rec_html = "<strong>%s</strong>/%s" % (
                        rec, e.get("total", ""))
                else:
                    rec_html = "—"
                late = (' <span class="b late">LATE</span>'
                        if e.get("is_late") else "")
                link = ('<a href="%s">open report</a>' % _esc(e["page"])
                        if e.get("page") else "")
                links_cell = [link]
                if e.get("speedgrader"):
                    links_cell.append(
                        '<a href="%s">SpeedGrader</a>'
                        % _esc_url(e["speedgrader"]))
                links_cell.append(
                    '<a href="%s">GitHub</a>' % _esc_url(e["pr_url"])
                    if e.get("pr_url") else "")
                pr = " · ".join(
                    l_ for l_ in links_cell if l_ and l_ not in (" · ",))
                rows.append(
                    '<tr data-team="%s"><td>%s%s<span class="mut small">'
                    " &middot; %s &middot; %s</span></td><td>%s</td>"
                    "<td>%s</td><td class='small'>%s</td></tr>" % (
                        _esc(e["team"]), _esc(e["name"]), late,
                        _esc(e["netid"]), _esc(e["canvas_id"]),
                        _esc(e["team"]), rec_html, pr))

            body = ["<table>%s%s</table>" % (cols, "".join(rows))]
            if gaps:
                body.append(
                    "<h3>Member gap in team deliverable</h3><table>"
                    "<tr><th>team</th><th>student</th><th>netid</th></tr>%s"
                    "</table>" % "".join(
                        '<tr class="warnrow" data-team="%s"><td>%s</td>'
                        "<td>%s</td><td>%s</td></tr>"
                        % (_esc(g["team"]), _esc(g["team"]),
                           _esc(g["name"]), _esc(g["iu"])) for g in gaps))
            if exc:
                body.append(
                    "<h3>Needs TA review — tool produced no report</h3>"
                    "<table><tr><th>student</th><th>file</th><th>error"
                    "</th></tr>%s</table>" % "".join(
                        '<tr class="warnrow" data-team="%s"><td>%s<'
                        'span class="mut small"> · %s</span></td>'
                        "<td>%s</td><td>%s</td></tr>"
                        % (_esc(x["team"]), _esc(x["name"]),
                           _esc(x["netid"]), _esc(x["file"]),
                           _esc(x["error"])) for x in exc))
            if missing:
                body.append(
                    "<h3>MISSING — no Canvas submission file found</h3>"
                    "<table><tr><th>student</th><th>team</th>"
                    "<th>netid</th><th>TA</th></tr>%s</table>" % "".join(
                        '<tr class="warnrow" data-team="%s"><td>%s</td>'
                        "<td>%s</td><td>%s</td><td>%s</td></tr>"
                        % (_esc(m["team"]), _esc(m["name"]),
                           _esc(m["team"]), _esc(m["iu"]),
                           _esc(m.get("ta", ""))) for m in missing))

            summary_bits = "".join(b for b in badges if b)
            cards.append(
                '<details class="lane lane-sec"><a id="%s"></a>'
                "<summary>%s <span class='mut small'>(%s)</span>%s</summary>"
                '<div class="card links small">%s%s<em class="mut">'
                "run %s · re-runs overwrite these pages</em></div>%s"
                "</details>" % (
                    _esc(lane["lane"]),
                    _esc(lane["assignment_title"]),
                    _esc(lane["assignment_code"] or lane["lane"]),
                    (" " + summary_bits) if summary_bits.strip() else "",
                    ("<p>%s</p>" % canvas_link) if canvas_link else "",
                    '' if is_team else '',
                    _esc(lane["run_ts"]),
                    "".join(body)))
        week_blocks.append(
            '<section class="week"><h2 class="week-h">%s</h2>%s'
            "</section>" % (
                ("Week %d" % week) if week != 999
                else "(uncategorized)",
                "".join(cards)))

    page = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>SE1 FA26 — grading reports (TA view)</title>
<style>%s</style>
<script>%s</script>
</head><body><main>
<h1>SE1 FA26 &mdash; grading reports</h1>
<p class="small mut">Assignments grouped by week &mdash; click an
assignment to open its report list. Everything is <strong>recommended,
not final</strong>: open a student's report or SpeedGrader, review the
linked work, adjust for substance and the TAP Collaboration
Coefficient, then enter scores in the Canvas gradebook. Red badges on a
folded row mean gaps you must see
(<span class="b fail">exception</span> /
<span class="b fail">MISSING</span>). Re-runs overwrite; each
assignment's timestamp is its latest run. Filter with the chips.</p>
<div class="chips">%s</div>
%s
<footer>Generated %s &middot; icex_checker &middot; submissions/
report.html rebuilt on every batch run &middot; lanes: %s</footer>
</main></body></html>""" % (
        _CSS, _JS, "".join(chips), "".join(week_blocks), _esc(run_ts),
        _esc(", ".join(l["lane"] for l in lanes)))

    out = out_root / "report.html"
    out.write_text(page)
    return out
