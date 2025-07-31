from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.email import EmailOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta
import openstack
import requests
import time
import os
import json
from openstack.config import OpenStackConfig

AIRFLOW_HOST = "172.29.20.254"
APPROVAL_SERVER_URL = f"http://{AIRFLOW_HOST}:5000"  # or IP if remote
CLOUDS_YAML_PATH = "/home/ubuntu/apps/airflow/clouds.yaml"
DEFAULT_CLOUD = "sa-demo-region1"
ADMIN_EMAIL = "niket@platform9.com"

default_args = {
    "retries": 0,
    "retry_delay": timedelta(minutes=1)
}

def get_inputs(**context):
    conf = context["dag_run"].conf
    context['ti'].xcom_push(key='input_conf', value=conf)

def send_admin_email(**context):
    conf = context['ti'].xcom_pull(key='input_conf', task_ids='get_input')
    user_email = conf.get("user_email")
    dag_run_id = context["dag_run"].run_id
    approve_url = f"{APPROVAL_SERVER_URL}/approval?dag_run_id={dag_run_id}&status=approve"
    deny_url = f"{APPROVAL_SERVER_URL}/approval?dag_run_id={dag_run_id}&status=deny"

    html_content = f"""
    <h3>VM Creation Approval Request</h3>
    <p>User <b>{user_email}</b> has requested a VM.</p>
    <p><a href="{approve_url}">Approve</a> | <a href="{deny_url}">Deny</a></p>
    """

    # Send email via EmailOperator
    email = EmailOperator(
        task_id='send_admin_email',
        to=ADMIN_EMAIL,
        subject="Airflow Approve Request!",
        html_content=html_content
    )
    return email.execute(context=context)

def wait_for_approval(**context):
    dag_run_id = context["dag_run"].run_id
    timeout = 2 * 60  # 2 minutes
    poll_interval = 15  # seconds
    elapsed = 0

    while elapsed < timeout:
        resp = requests.get(f"{APPROVAL_SERVER_URL}/get_approval", params={"dag_run_id": dag_run_id})
        status = resp.json().get("status")
        if status in ["approve", "deny"]:
            context['ti'].xcom_push(key="approval_status", value=status)
            return
        time.sleep(poll_interval)
        elapsed += poll_interval

    context['ti'].xcom_push(key="approval_status", value="timeout")

def decide_next(**context):
    status = context['ti'].xcom_pull(key="approval_status", task_ids='wait_for_approval')
    if status == "approve":
        return "create_vm"
    else:
        return "send_denial_email"

def create_vm(**context):
    conf = context['ti'].xcom_pull(key='input_conf', task_ids='get_input')
    flavor = conf["flavor"]
    image = conf["image"]
    network = conf["network"]
    cloud = conf.get("cloud", DEFAULT_CLOUD)

    clouds = OpenStackConfig(config_files=[CLOUDS_YAML_PATH])
    cloud_config = clouds.get_one(cloud)
    conn = openstack.connection.Connection(config=cloud_config)

    flavor_obj = conn.compute.find_flavor(flavor)
    image_obj = conn.compute.find_image(image)
    network_obj = conn.network.find_network(network)

    if not all([flavor_obj, image_obj, network_obj]):
        raise Exception("Could not find resources.")

    vm_name = f"airflow-vm-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    server = conn.compute.create_server(
        name=vm_name,
        image_id=image_obj.id,
        flavor_id=flavor_obj.id,
        networks=[{"uuid": network_obj.id}]
    )
    conn.compute.wait_for_server(server)
    context['ti'].xcom_push(key='vm_name', value=vm_name)

def send_success_email(**context):
    conf = context['ti'].xcom_pull(key='input_conf', task_ids='get_input')
    user_email = conf.get("user_email")
    vm_name = context['ti'].xcom_pull(key='vm_name', task_ids='create_vm')

    html_content = f"""
    <h3>VM Created Successfully</h3>
    <p>VM Name: <b>{vm_name}</b></p>
    """

    email = EmailOperator(
        task_id='send_success_email',
        to=user_email,
        subject="Your VM has been created!",
        html_content=html_content
    )
    return email.execute(context=context)

def send_denial_email(**context):
    conf = context['ti'].xcom_pull(key='input_conf', task_ids='get_input')
    user_email = conf.get("user_email")
    html_content = "<h3>VM Creation Denied</h3><p>Admin has denied the request.</p>"

    email = EmailOperator(
        task_id='send_denial_email',
        to=user_email,
        subject="VM Creation Request Denied!",
        html_content=html_content
    )
    return email.execute(context=context)

with DAG(
    dag_id="openstack_vm_creator_approval_flow",
    start_date=datetime(2025, 7, 25),
    schedule=None,
    catchup=False,
    default_args=default_args,
    tags=["openstack", "approval", "vm"]
) as dag:

    get_input = PythonOperator(
        task_id="get_input",
        python_callable=get_inputs
    )

    send_admin_email = PythonOperator(
        task_id="send_admin_email",
        python_callable=send_admin_email
    )

    wait_for_approval = PythonOperator(
        task_id="wait_for_approval",
        python_callable=wait_for_approval
    )

    decide = BranchPythonOperator(
        task_id="decide_next_step",
        python_callable=decide_next
    )

    create_vm = PythonOperator(
        task_id="create_vm",
        python_callable=create_vm
    )

    send_success_email = PythonOperator(
        task_id="send_success_email",
        python_callable=send_success_email,
        trigger_rule=TriggerRule.ALL_SUCCESS
    )

    send_denial_email = PythonOperator(
        task_id="send_denial_email",
        python_callable=send_denial_email,
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS
    )

    end = EmptyOperator(task_id="end", trigger_rule=TriggerRule.ALL_DONE)

    get_input >> send_admin_email >> wait_for_approval >> decide
    decide >> create_vm >> send_success_email >> end
    decide >> send_denial_email >> end