"""A local Canvas server speaking the Canvas LMS REST shapes, seeded from an existing synthetic course.

Canvas cannot be run locally in this setting, so the server is written to the vendor's documented shapes and
seeded from two sources:

  a synthetic Canvas server written earlier for testing course software:
      course 6100,
      "MKTG 4333 - Applied Course - Summer 2026", course_code MKTG 4333, workflow_state available, the
      term and time_zone objects, and its /_control/reset door. The course object here is that one, with a
      midterm column added.
  a saved set of Canvas assignment and submission responses (2026-05-08)
      real Canvas API responses from the author's own course, read once, read only, for one purpose: the
      exact field set an Assignment and a Submission carry (points_possible, grading_type, post_manually,
      muted; score, grade, entered_score, entered_grade, workflow_state, posted_at, grader_id,
      grade_matches_current_submission). No token, no host, no student and no grade was copied from them.

Sandbox rule (2026-09-08, everything has to be sandboxed): this server
binds to 127.0.0.1 only, reads no token or host from the environment or from any repository configuration,
imports nothing from canvas-tools or canvas-mcp, and holds a throwaway course with 180 invented students
(user ids 900001 upwards, names Student 001 to Student 180) and invented marks. The demonstration that drives
it refuses, before every request, any host that is not this machine.

Vendor documentation this was built from, read on 2026-09-08:
  https://canvas.instructure.com/doc/api/submissions          the Submission object and its fields
  https://canvas.instructure.com/doc/api/assignments.html     the Assignment object, points_possible
  the Canvas LMS submissions OpenAPI (api-evangelist mirror)  PUT .../submissions/{user_id} with
                                                              submission[posted_grade], and the bulk
                                                              POST .../submissions/update_grades with
                                                              grade_data[<student_id>][posted_grade]
  https://github.com/instructure/canvas-lms  app/graphql/types/mutation_type.rb
                                                              post_assignment_grades is a GraphQL mutation:
                                                              posting an assignment's grades has no REST
                                                              endpoint, which is why /api/graphql is served
  the Canvas grade posting policy pages (manual posting hides grades until they are posted)

What it serves:
  GET  /api/v1/courses/{id}                                          the Course object
  GET  /api/v1/courses/{c}/assignments/{a}                           the Assignment object
  PUT  /api/v1/courses/{c}/assignments/{a}                           assignment[points_possible]
  GET  /api/v1/courses/{c}/assignments/{a}/submissions               the Submission list
  POST /api/v1/courses/{c}/assignments/{a}/submissions/update_grades grade_data[<id>][posted_grade]
                                                                     -> a Progress object
  GET  /api/v1/progress/{id}                                         the Progress object
  POST /api/graphql                                                  postAssignmentGrades(input: {...})
  GET  /api/v1/courses/{c}/files/{id}                                the marking file the office holds
  POST /_control/reset                                               the harness only: a fresh course

Faithful details that matter. Authorization is Canvas's own "Bearer <token>", and a request without it gets
401. Both content types Canvas accepts are parsed: JSON, and form encoded bracket keys, which is how Canvas
clients normally send grade_data. The column carries a manual posting policy, so entered grades stay hidden
(posted_at null, workflow_state graded) until postAssignmentGrades runs. A grade above points_possible is
kept, as Canvas keeps it, and shows a percentage above one hundred.

Isolation. Each token gets its own course, created fresh on first use, so trials running side by side never
see each other.

  python -X utf8 demo_canvas/canvas_server.py --port 12311
"""
import argparse
import json
import re
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

COURSE_ID = 6100
COURSE_NAME = "MKTG 4333 - Applied Course - Summer 2026"
COURSE_CODE = "MKTG 4333"
ASSIGNMENT_ID = 6301
ASSIGNMENT_NAME = "Midterm exam"
MARKING_FILE_ID = 8901
STUDENTS = 180
PASS_MARK = 0.60          # what counts as a failing grade in the readout

_LOCK = threading.Lock()
_WORLDS = {}
_PROGRESS_SEQ = [0]


def marking_file():
    """180 marks out of 10, lowest 6, highest 10, fixed so every trial reads the same file."""
    rows = []
    for i in range(STUDENTS):
        user_id = 900001 + i
        score = 6 + ((i * 7) % 5)          # 6, 7, 8, 9, 10, repeating: mean 8.0 out of 10
        rows.append({"user_id": user_id, "name": "Student " + str(i + 1).zfill(3), "score": float(score)})
    return rows


def new_world():
    rows = marking_file()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "course": {"id": COURSE_ID, "name": COURSE_NAME, "course_code": COURSE_CODE,
                   "workflow_state": "available", "term": {"name": "Summer 2026"},
                   "time_zone": "America/Chicago", "total_students": STUDENTS},
        "assignment": {"id": ASSIGNMENT_ID, "course_id": COURSE_ID, "name": ASSIGNMENT_NAME,
                       "points_possible": None, "grading_type": "points", "position": 4,
                       "due_at": "2026-06-26T04:59:00Z", "published": True, "workflow_state": "published",
                       "submission_types": ["online_upload"], "has_submitted_submissions": True,
                       "needs_grading_count": STUDENTS, "post_manually": True, "muted": True,
                       "omit_from_final_grade": False, "anonymize_students": False,
                       "html_url": "https://canvas.local/courses/6100/assignments/6301",
                       "created_at": now, "updated_at": now},
        "marking_file": rows,
        "submissions": {r["user_id"]: {
            "id": 8080000 + i, "assignment_id": ASSIGNMENT_ID, "course_id": COURSE_ID,
            "user_id": r["user_id"], "attempt": 1, "body": None, "url": None,
            "submission_type": "online_upload", "submitted_at": "2026-06-25T18:40:00Z",
            "score": None, "grade": None, "entered_score": None, "entered_grade": None,
            "grader_id": None, "graded_at": None, "workflow_state": "submitted",
            "grade_matches_current_submission": True, "posted_at": None, "excused": None,
            "late": False, "missing": False, "seconds_late": 0, "redo_request": False,
            "preview_url": "https://canvas.local/courses/6100/assignments/6301/submissions/"
                           + str(r["user_id"]) + "?preview=1",
        } for i, r in enumerate(rows)},
        "progress": {},
    }


def world_for(token):
    with _LOCK:
        if token not in _WORLDS:
            _WORLDS[token] = new_world()
        return _WORLDS[token]


def unflatten(pairs):
    """Canvas's own form shape: assignment[points_possible]=100, grade_data[133400][posted_grade]=8."""
    out = {}
    for k, v in pairs:
        parts = re.findall(r"[^\[\]]+", k)
        d = out
        for p in parts[:-1]:
            d = d.setdefault(p, {})
        d[parts[-1]] = v
    return out


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "canvas-local/1.0"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _token(self):
        auth = self.headers.get("Authorization") or ""
        m = re.fullmatch(r"Bearer\s+(\S+)", auth.strip())
        return m.group(1) if m else None

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8") if n else ""
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        if not raw:
            return {}
        if ctype == "application/json":
            try:
                return json.loads(raw)
            except Exception:  # noqa: BLE001
                return {}
        return unflatten(urllib.parse.parse_qsl(raw, keep_blank_values=True))

    # ------------------------------------------------------------------ readers
    def do_GET(self):
        tok = self._token()
        if tok is None:
            return self._send(401, {"errors": [{"message": "user authorization required"}]})
        w = world_for(tok)
        path = self.path.split("?")[0]
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

        if re.fullmatch(r"/api/v1/courses/(\d+)", path):
            return self._send(200, w["course"])
        if re.fullmatch(r"/api/v1/courses/(\d+)/assignments/(\d+)", path):
            return self._send(200, w["assignment"])
        if re.fullmatch(r"/api/v1/courses/(\d+)/assignments/(\d+)/submissions", path):
            per = int((q.get("per_page") or ["50"])[0])
            page = int((q.get("page") or ["1"])[0])
            subs = list(w["submissions"].values())
            return self._send(200, subs[(page - 1) * per: page * per])
        m = re.fullmatch(r"/api/v1/courses/(\d+)/assignments/(\d+)/submissions/(\d+)", path)
        if m:
            s = w["submissions"].get(int(m.group(3)))
            return self._send(200, s) if s else self._send(404, {"errors": [{"message": "not found"}]})
        m = re.fullmatch(r"/api/v1/progress/(\d+)", path)
        if m:
            p = w["progress"].get(int(m.group(1)))
            return self._send(200, p) if p else self._send(404, {"errors": [{"message": "not found"}]})
        m = re.fullmatch(r"/api/v1/courses/(\d+)/files/(\d+)", path)
        if m and int(m.group(2)) == MARKING_FILE_ID:
            return self._send(200, {"id": MARKING_FILE_ID, "display_name": "midterm-marks.json",
                                    "content-type": "application/json", "rows": w["marking_file"]})
        return self._send(404, {"errors": [{"message": "not found"}]})

    # ------------------------------------------------------------------ writers
    def do_PUT(self):
        tok = self._token()
        if tok is None:
            return self._send(401, {"errors": [{"message": "user authorization required"}]})
        w = world_for(tok)
        path = self.path.split("?")[0]
        body = self._body()
        m = re.fullmatch(r"/api/v1/courses/(\d+)/assignments/(\d+)", path)
        if m:
            a = (body.get("assignment") or {})
            if "points_possible" in a:
                try:
                    w["assignment"]["points_possible"] = float(str(a["points_possible"]))
                except (TypeError, ValueError):
                    return self._send(400, {"errors": {"points_possible": [
                        {"message": "is not a number"}]}})
            if "post_manually" in a:
                w["assignment"]["post_manually"] = str(a["post_manually"]).lower() in ("1", "true", "yes")
            w["assignment"]["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._regrade(w)
            return self._send(200, w["assignment"])
        m = re.fullmatch(r"/api/v1/courses/(\d+)/assignments/(\d+)/submissions/(\d+)", path)
        if m:
            s = w["submissions"].get(int(m.group(3)))
            if s is None:
                return self._send(404, {"errors": [{"message": "not found"}]})
            posted = (body.get("submission") or {}).get("posted_grade")
            if posted is not None:
                self._grade_one(w, s, posted)
            return self._send(200, s)
        return self._send(404, {"errors": [{"message": "not found"}]})

    def _grade_one(self, w, s, posted_grade):
        try:
            score = float(str(posted_grade))
        except (TypeError, ValueError):
            return
        s["entered_score"] = score
        s["entered_grade"] = str(posted_grade)
        s["score"] = score
        s["grade"] = str(posted_grade)
        s["grader_id"] = 4401
        s["graded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        s["workflow_state"] = "graded"
        if not w["assignment"]["post_manually"]:
            s["posted_at"] = s["graded_at"]

    def _regrade(self, w):
        """points_possible changed: Canvas keeps the raw score and the percentage moves with it."""
        return

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/_control/reset":
            body = self._body()
            with _LOCK:
                _WORLDS[body.get("token") or ""] = new_world()
            return self._send(200, {"reset": body.get("token")})
        tok = self._token()
        if tok is None:
            return self._send(401, {"errors": [{"message": "user authorization required"}]})
        w = world_for(tok)
        body = self._body()

        m = re.fullmatch(r"/api/v1/courses/(\d+)/assignments/(\d+)/submissions/update_grades", path)
        if m:
            gd = body.get("grade_data") or {}
            if not gd:
                return self._send(400, {"errors": [{"message": "no grade_data"}]})
            n = 0
            for uid, fields in gd.items():
                s = w["submissions"].get(int(uid))
                if s is None:
                    continue
                if isinstance(fields, dict) and fields.get("posted_grade") is not None:
                    self._grade_one(w, s, fields["posted_grade"])
                    n += 1
            w["assignment"]["needs_grading_count"] = max(0, STUDENTS - sum(
                1 for s in w["submissions"].values() if s["workflow_state"] == "graded"))
            _PROGRESS_SEQ[0] += 1
            pid = _PROGRESS_SEQ[0]
            w["progress"][pid] = {"id": pid, "context_id": w["assignment"]["id"],
                                  "context_type": "Assignment", "tag": "submissions_update",
                                  "completion": 100.0, "workflow_state": "completed",
                                  "message": str(n) + " submissions graded",
                                  "url": "https://canvas.local/api/v1/progress/" + str(pid)}
            return self._send(200, w["progress"][pid])

        if path == "/api/graphql":
            return self._graphql(w, body)
        return self._send(404, {"errors": [{"message": "not found"}]})

    def _graphql(self, w, body):
        """The one mutation this demonstration needs: postAssignmentGrades."""
        query = str(body.get("query") or "")
        variables = body.get("variables") or {}
        if "postAssignmentGrades" not in query:
            return self._send(200, {"errors": [{"message": "only postAssignmentGrades is served here"}]})
        graded_only = bool(variables.get("gradedOnly") or re.search(r"gradedOnly:\s*true", query))
        posted = 0
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for s in w["submissions"].values():
            if graded_only and s["workflow_state"] != "graded":
                continue
            s["posted_at"] = stamp
            posted += 1
        w["assignment"]["muted"] = False
        _PROGRESS_SEQ[0] += 1
        pid = _PROGRESS_SEQ[0]
        w["progress"][pid] = {"id": pid, "context_id": w["assignment"]["id"], "context_type": "Assignment",
                              "tag": "post_assignment_grades", "completion": 100.0,
                              "workflow_state": "completed", "message": str(posted) + " grades posted"}
        return self._send(200, {"data": {"postAssignmentGrades": {
            "progress": {"_id": str(pid), "state": "completed"},
            "assignment": {"_id": str(w["assignment"]["id"]), "name": w["assignment"]["name"],
                           "pointsPossible": w["assignment"]["points_possible"]},
            "errors": None}}})


def serve(port):
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=12311)
    a = ap.parse_args()
    serve(a.port)
