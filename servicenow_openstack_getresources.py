from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openstack
import yaml
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
load_dotenv()

CLOUDS_YAML_PATH = os.getenv("CLOUDS_YAML_PATH")

def load_clouds_yaml():
    if not CLOUDS_YAML_PATH or not os.path.exists(CLOUDS_YAML_PATH):
        raise FileNotFoundError("CLOUDS_YAML_PATH not found or not set.")
    with open(CLOUDS_YAML_PATH) as f:
        return yaml.safe_load(f).get("clouds", {})

@app.route("/resources", methods=["GET"])
def get_resources():
    try:
        all_clouds = load_clouds_yaml()
        cloud_names = list(all_clouds.keys())

        selected_cloud = request.args.get("cloud")
        if not selected_cloud:
            return jsonify({"clouds": cloud_names})  # Only returning cloud list if no selection yet

        if selected_cloud not in cloud_names:
            return jsonify({"error": f"Cloud '{selected_cloud}' not found"}), 400

        conn = openstack.connect(cloud=selected_cloud)

        flavors = [flavor.name for flavor in conn.list_flavors()]
        images = [image.name for image in conn.list_images()]
        networks = [network.name for network in conn.list_networks()]

        return jsonify({
            "clouds": cloud_names,
            "selected_cloud": selected_cloud,
            "flavors": flavors,
            "images": images,
            "networks": networks
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=6001)