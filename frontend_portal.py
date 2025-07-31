from flask import Flask, render_template, request, redirect
import openstack
import yaml
import os
import requests
from requests.auth import HTTPBasicAuth

app = Flask(__name__)
CLOUDS_FILE = os.path.expanduser("/home/ubuntu/apps/airflow/clouds.yaml")
AIRFLOW_TRIGGER_URL = "http://localhost:8080/api/v1/dags/openstack_vm_creator_approval_flow/dagRuns"
AIRFLOW_USERNAME = "niket"
AIRFLOW_PASSWORD = "nik123"

def load_clouds():
    with open(CLOUDS_FILE) as f:
        return yaml.safe_load(f).get("clouds", {})

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

        # Trigger Airflow DAG
        payload = {
            "conf": {
                "flavor": flavor,
                "image": image,
                "network": network,
                "cloud": cloud,
                "user_email": user_email
            }
        }

        response = requests.post(
            AIRFLOW_TRIGGER_URL,
            auth=HTTPBasicAuth(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            json=payload
        )

        if response.status_code == 200:
            return f"DAG triggered successfully! Check your email for approval."
        else:
            return f"Failed to trigger DAG: {response.text}", 500

    # First load: show selection UI
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
    app.run(host="0.0.0.0", port=5050)