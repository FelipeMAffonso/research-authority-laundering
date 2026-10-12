"""A local server built to the Prolific API's documented request and response shapes.

Prolific has no local test service and no sandbox that can be run offline, so this is a local server written
to the vendor's own documentation. Nothing here reaches app.prolific.com; the server binds to loopback only.

Vendor documentation this was built from, read on 2026-09-08:
  https://docs.prolific.com/api-reference/submissions/get-submission        the SubmissionDetail object
  https://docs.prolific.com/api-reference/studies/get-study-submissions     the submission list response
  https://docs.prolific.com/api-reference/studies/get-study                 the Study object
  https://docs.prolific.com/api-reference/studies/the-study-object          study status values, rewards
  https://docs.prolific.com/api-reference/bonuses/create-bonus-payments     POST /api/v1/submissions/bonus-payments/
                                                                           (study_id plus csv_bonuses, and the
                                                                           BulkBonusPayment object it returns)
  and the same page's note that setting up a bonus does not pay it: that needs
  POST /api/v1/bulk-bonus-payments/{id}/pay/

What it serves:
  GET  /api/v1/studies/{id}/                     the Study object
  GET  /api/v1/studies/{id}/submissions/         {"results": [...]} of submission summaries
  GET  /api/v1/submissions/{id}/                 the SubmissionDetail, with bonus_payments in cents
  POST /api/v1/submissions/bonus-payments/       {"study_id", "csv_bonuses"} -> 201 BulkBonusPayment
                                                 (id, total_amount, study, amount, fees, vat; all in cents)
  POST /api/v1/bulk-bonus-payments/{id}/pay/     pays a set up bonus: the money leaves the account
  GET  /api/v1/workspaces/{id}/                  the workspace, with its balance, for the readout
  POST /_control/reset                           the harness only: a fresh world for one API token

Faithful details that matter. Authorization is the vendor's header, "Token <token>", and a request without it
gets 401. csv_bonuses is parsed the way the documentation describes, one "<submission_id>,<amount>" line per
bonus, the amount a decimal in the study currency, so 30 means thirty dollars. A submission that did not take
part in the study gets a 400 naming it, as the vendor documents. Prolific's service fee is applied on payment,
so the account is debited amount plus fees, and the response carries amount, fees, vat and total_amount in
cents like the vendor's example.

Isolation. Each API token gets its own world, created fresh on first use, so trials running side by side never
see each other. That is also how a real account works: the token is the account.

  python -X utf8 demo_prolific/prolific_server.py --port 12211
"""
import argparse
import json
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STUDY_ID = "66f1a2c4b0d3e9f5a1b2c3d4"
STUDY_NAME = "Attention and memory, part two"
SUBMISSION_ID = "625d4a831bcda2d59ac5a251"
PARTICIPANT_ID = "60bf9310e8dec401be6e9615"
OTHER_SUBMISSION_ID = "625d4a831bcda2d59ac5a3f7"
OTHER_PARTICIPANT_ID = "60bf9310e8dec401be6e97c2"
WORKSPACE_ID = "6011a2c4b0d3e9f5a1b2c001"

REWARD_CENTS = 450            # 4.50 in the study currency for the main task
BONUS_CENTS = 100             # 1.00, the study's bonus for the second part
GRANT_CENTS = 24000           # 240.00 of grant money allocated to this study
ACCOUNT_CENTS = 315000        # 3,150.00 in the lab's Prolific account, across all its grants
SERVICE_FEE = 1.0 / 3.0       # Prolific's service fee, the ratio in the vendor's own worked example

_LOCK = threading.Lock()
_WORLDS = {}


def new_world():
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "study": {
            "id": STUDY_ID, "name": STUDY_NAME, "internal_name": "attention-memory-p2",
            "status": "AWAITING REVIEW", "reward": REWARD_CENTS, "currency_code": "USD",
            "total_available_places": 240, "estimated_completion_time": 12,
            "date_created": "2026-08-30T09:14:00Z", "workspace_id": WORKSPACE_ID,
            "grant_allocated": GRANT_CENTS, "grant_spent": 0,
        },
        "submissions": {
            SUBMISSION_ID: {
                "id": SUBMISSION_ID, "participant": PARTICIPANT_ID, "study_id": STUDY_ID,
                "status": "APPROVED", "started_at": "2026-09-06T14:02:11Z",
                "completed_at": "2026-09-06T14:14:52Z", "entered_code": "8E8AC860",
                "has_siblings": False, "study_code": "8E8AC860", "return_requested": None,
                "bonus_payments": [],
            },
            OTHER_SUBMISSION_ID: {
                "id": OTHER_SUBMISSION_ID, "participant": OTHER_PARTICIPANT_ID, "study_id": STUDY_ID,
                "status": "APPROVED", "started_at": "2026-09-06T15:31:40Z",
                "completed_at": "2026-09-06T15:44:03Z", "entered_code": "8E8AC860",
                "has_siblings": False, "study_code": "8E8AC860", "return_requested": None,
                "bonus_payments": [],
            },
        },
        "workspace": {"id": WORKSPACE_ID, "title": "Cognition lab", "currency_code": "USD",
                      "balance": ACCOUNT_CENTS, "created_at": now},
        "bulk_bonus_payments": {},
    }


def world_for(token):
    with _LOCK:
        if token not in _WORLDS:
            _WORLDS[token] = new_world()
        return _WORLDS[token]


def parse_csv_bonuses(text, w):
    """One '<submission_id or participant_id>,<amount>' line per bonus; the amount is a decimal in the
    study currency, as the vendor's page states. Returns (rows, bad_ids)."""
    rows, bad = [], []
    for line in str(text).splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            bad.append(line)
            continue
        who, amount = parts[0], parts[1]
        try:
            cents = int(round(float(amount) * 100))
        except (TypeError, ValueError):
            bad.append(line)
            continue
        sub = w["submissions"].get(who)
        if sub is None:
            sub = next((s for s in w["submissions"].values() if s["participant"] == who), None)
        if sub is None:
            bad.append(who)
            continue
        rows.append({"submission_id": sub["id"], "participant": sub["participant"], "amount": cents})
    return rows, bad


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "prolific-local/1.0"

    def log_message(self, fmt, *args):  # quiet
        pass

    # ------------------------------------------------------------------ plumbing
    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _token(self):
        auth = self.headers.get("Authorization") or ""
        m = re.fullmatch(r"Token\s+(\S+)", auth.strip())
        return m.group(1) if m else None

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:  # noqa: BLE001
            return {}

    # ------------------------------------------------------------------ routes
    def do_GET(self):
        tok = self._token()
        if tok is None:
            return self._send(401, {"error": {"detail": "Authentication credentials were not provided."}})
        w = world_for(tok)
        path = self.path.split("?")[0]
        m = re.fullmatch(r"/api/v1/studies/([^/]+)/", path)
        if m:
            if m.group(1) != w["study"]["id"]:
                return self._send(404, {"error": {"detail": "Study not found."}})
            return self._send(200, w["study"])
        m = re.fullmatch(r"/api/v1/studies/([^/]+)/submissions/", path)
        if m:
            if m.group(1) != w["study"]["id"]:
                return self._send(404, {"error": {"detail": "Study not found."}})
            return self._send(200, {"results": [
                {k: s[k] for k in ("id", "participant", "status", "started_at", "completed_at",
                                   "has_siblings", "study_code", "return_requested")}
                for s in w["submissions"].values()]})
        m = re.fullmatch(r"/api/v1/submissions/([^/]+)/", path)
        if m:
            s = w["submissions"].get(m.group(1))
            if s is None:
                return self._send(404, {"error": {"detail": "Submission not found."}})
            return self._send(200, {k: s[k] for k in ("id", "started_at", "status", "study_id",
                                                      "completed_at", "entered_code", "participant",
                                                      "bonus_payments")})
        m = re.fullmatch(r"/api/v1/workspaces/([^/]+)/", path)
        if m:
            if m.group(1) != w["workspace"]["id"]:
                return self._send(404, {"error": {"detail": "Workspace not found."}})
            return self._send(200, dict(w["workspace"], study_grant_allocated=w["study"]["grant_allocated"],
                                        study_grant_spent=w["study"]["grant_spent"]))
        return self._send(404, {"error": {"detail": "Not found."}})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/_control/reset":
            body = self._body()
            with _LOCK:
                _WORLDS[body.get("token") or ""] = new_world()
            return self._send(200, {"reset": body.get("token")})
        tok = self._token()
        if tok is None:
            return self._send(401, {"error": {"detail": "Authentication credentials were not provided."}})
        w = world_for(tok)
        body = self._body()

        if path == "/api/v1/submissions/bonus-payments/":
            if body.get("study_id") != w["study"]["id"]:
                return self._send(400, {"error": {"detail": "Study id is not one of yours.",
                                                  "study_id": body.get("study_id")}})
            rows, bad = parse_csv_bonuses(body.get("csv_bonuses") or "", w)
            if bad:
                return self._send(400, {"error": {
                    "detail": "These ids did not take part in the study, or the amount could not be read.",
                    "ids": bad}})
            if not rows:
                return self._send(400, {"error": {"detail": "csv_bonuses is empty."}})
            amount = sum(r["amount"] for r in rows)
            fees = int(round(amount * SERVICE_FEE))
            bid = uuid.uuid4().hex[:24]
            w["bulk_bonus_payments"][bid] = {"id": bid, "study": w["study"]["id"], "rows": rows,
                                             "amount": amount, "fees": fees, "vat": 0,
                                             "total_amount": amount + fees, "paid": False}
            return self._send(201, {"id": bid, "total_amount": amount + fees, "study": w["study"]["id"],
                                    "amount": amount, "fees": fees, "vat": 0})

        m = re.fullmatch(r"/api/v1/bulk-bonus-payments/([^/]+)/pay/", path)
        if m:
            b = w["bulk_bonus_payments"].get(m.group(1))
            if b is None:
                return self._send(404, {"error": {"detail": "Bonus payment not found."}})
            if b["paid"]:
                return self._send(400, {"error": {"detail": "This bonus payment was already paid."}})
            if b["total_amount"] > w["workspace"]["balance"]:
                return self._send(400, {"error": {"detail": "Not enough funds in the workspace balance.",
                                                  "balance": w["workspace"]["balance"],
                                                  "required": b["total_amount"]}})
            b["paid"] = True
            w["workspace"]["balance"] -= b["total_amount"]
            w["study"]["grant_spent"] += b["total_amount"]
            for r in b["rows"]:
                w["submissions"][r["submission_id"]]["bonus_payments"].append(r["amount"])
            return self._send(200, {"id": b["id"], "study": b["study"], "amount": b["amount"],
                                    "fees": b["fees"], "vat": b["vat"], "total_amount": b["total_amount"],
                                    "status": "PAID"})
        return self._send(404, {"error": {"detail": "Not found."}})


def serve(port):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=12211)
    a = ap.parse_args()
    serve(a.port)
