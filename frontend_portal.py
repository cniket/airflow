from dotenv import load_dotenv
from flask import Flask, render_template, request
from datetime import datetime, timezone
import openstack
import yaml
import os
import requests

load_dotenv()

app = Flask(__name__)

AIRFLOW_HOST = os.getenv("AIRFLOW_HOST")
AIRFLOW_PORT = os.getenv("AIRFLOW_PORT", "8080")
DAG_ID = os.getenv("DAG_ID")
JWT_TOKEN_FILE = os.getenv("JWT_TOKEN_FILE")
CLOUDS_FILE = os.getenv("CLOUDS_YAML_PATH")
FRONTEND_SERVER_PORT = os.getenv("FRONTEND_SERVER_PORT", "5050")

# Airflow DAG trigger endpoint
AIRFLOW_TRIGGER_URL = f"http://{AIRFLOW_HOST}:{AIRFLOW_PORT}/api/v2/dags/{DAG_ID}/dagRuns"

def load_clouds():
    with open(CLOUDS_FILE) as f:
        return yaml.safe_load(f).get("clouds", {})

def get_jwt_token():
    if os.path.exists(JWT_TOKEN_FILE):
        with open(JWT_TOKEN_FILE) as f:
            return f.read().strip()
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    clouds = load_clouds()
    cloud_names = list(clouds.keys())

    if request.method == "POST":
        cloud = request.form["cloud"]
        user_email = request.form["user_email"]
        flavor = request.form["flavor"]
        image = request.form["image"]
        network = request.form["network"]

        # Construct payload for Airflow DAG
        payload = {
            "conf": {
                "flavor": flavor,
                "image": image,
                "network": network,
                "cloud": cloud,
                "user_email": user_email
            },
            "logical_date": datetime.now(timezone.utc).isoformat()
        }

        token = get_jwt_token()
        if not token:
            return "Error: JWT token not found.", 500

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        dag_info = requests.get(AIRFLOW_TRIGGER_URL, headers=headers)
        if dag_info.status_code == 200:
            is_paused = dag_info.json().get("is_paused", True)
            print(f"DAG is paused: {is_paused}")
            if is_paused:
                unpause_url =  f"http://{AIRFLOW_HOST}:{AIRFLOW_PORT}/api/v2/dags/{DAG_ID}"
                unpause_response = requests.patch(unpause_url, headers=headers, json={"is_paused": False})
                if unpause_response.status_code != 200:
                    return f"Failed to unpause DAG: {unpause_response.status_code} - {unpause_response.text}", 500
        else:
            return f"Failed to get DAG info: {dag_info.status_code} - {dag_info.text}", 500

        # Trigger the DAG run
        response = requests.post(
            AIRFLOW_TRIGGER_URL,
            headers=headers,
            json=payload
        )

        if response.status_code in (200, 201):  # 201 is common for created DAG runs
            return "DAG triggered successfully! Check your email for approval."
        else:
            return f"Failed to trigger DAG: {response.status_code} - {response.text}", 500

    # GET method - Show dropdowns
    selected_cloud = request.args.get("cloud", cloud_names[0])
    conn = openstack.connect(cloud=selected_cloud)

    flavors = conn.list_flavors()
    images = conn.list_images()
    networks = conn.list_networks()

    return render_template("form.html",
        clouds=cloud_names,
        selected_cloud=selected_cloud,
        flavors=flavors,
        images=images,
        networks=networks
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(FRONTEND_SERVER_PORT), debug=True)