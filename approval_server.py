# approval_server.py
from flask import Flask, request, jsonify
import json, os
from dotenv import load_dotenv

load_dotenv()

APPROVAL_SERVER_PORT = os.getenv("APPROVAL_SERVER_PORT", "5000")

app = Flask(__name__)
APPROVAL_FILE = "approvals.json"

def normalize_dag_run_id(dag_run_id):
    return dag_run_id.replace(" ", "+")

def load_approvals():
    if os.path.exists(APPROVAL_FILE):
        with open(APPROVAL_FILE) as f:
            return json.load(f)
    return {}

def save_approval(dag_run_id, status):
    dag_run_id = normalize_dag_run_id(dag_run_id)
    approvals = load_approvals()
    approvals[dag_run_id] = status
    with open(APPROVAL_FILE, "w") as f:
        json.dump(approvals, f, indent=2)

@app.route("/", methods=["GET"])
def index():
    return "Flask app is running!"

@app.route("/approval", methods=["GET"])
def approval():
    dag_run_id = request.args.get("dag_run_id")
    status = request.args.get("status")
    if not dag_run_id or status not in ("approve", "deny"):
        return "Invalid request", 400
    save_approval(dag_run_id, status)
    return f"Approval status '{status}' recorded for DAG run {dag_run_id}"

@app.route("/get_approval", methods=["GET"])
def get_approval():
    dag_run_id = request.args.get("dag_run_id")
    dag_run_id = normalize_dag_run_id(dag_run_id)
    approvals = load_approvals()
    return jsonify({"status": approvals.get(dag_run_id)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(APPROVAL_SERVER_PORT), debug=True)