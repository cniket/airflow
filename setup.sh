#!/bin/bash
set -e

mkdir -p apps/Airflow
cd apps/airflow/
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .airflow-venv
source .airflow-venv/bin/activate

export AIRFLOW_HOME=$(pwd)
echo AIRFLOW_HOME=$AIRFLOW_HOME >> ~/.bashrc
AIRFLOW_VERSION=3.0.4
export PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
export  CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
uv pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
uv pip install apache-airflow-providers-fab
uv pip install setuptools pip flask_appbuilder flask_cors openstacksdk

#uv pip install setuptools flask_appbuilder openstacksdk
#uv pip install apache-airflow apache-airflow-providers-fab

echo "[*] Configuring systemd services"
sudo cp systemd-units/airflow.service /etc/systemd/system/
sudo cp systemd-units/airflow-approval-server.service /etc/systemd/system/
sudo cp systemd-units/airflow-frontend-portal.service /etc/systemd/system/

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
#sudo systemctl enable airflow.service airflow-approval-server.service airflow-frontend-portal.service
sudo systemctl start airflow.service airflow-approval-server.service airflow-frontend-portal.service

echo "[*] Setup complete"
