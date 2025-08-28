# OpenStack VM Creator Approval Flow

This project provides an ServiceNow-Airflow-PCD based workflow for requesting, approving, and provisioning OpenStack VMs using either ServiceNow or a simple Flask application as a frontend and admin approval process.

## Project Structure

- `dags/`: Contains Airflow DAGs (notably `vm_creator_notify.py`).
- `approval_server.py`: Flask server for handling approval/denial of VM requests.
- `frontend_portal.py`: Flask frontend for users to request VMs.
- `templates/form.html`: HTML form that the frontend portal uses for VM request.
- `clouds.yaml`: OpenStack cloud configuration (see `clouds.yaml.template` for format).
- `.env`: Environment variables for configuration.
- `.jwt_token`: JWT token for Airflow API authentication.
- `run_airflow.sh`: Script to start all Airflow components.

## Setup

1. **Install Airflow in a virtual environment and configure it**
   
   1.1 Install airflow and clone this repo.
   ```
   ./setup.sh
   ```

   1.2 Add Fab auth manager if we want to authenticate to the airflow API using token.
   ```
   vim airflow.cfg
   [...]
   auth_manager = airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager
   ```
   
   1.3 Add JWT token secret key, again only required when authenticating to airflow API using token(like from servicenow). For this first create two random keys and then add those keys in the `airflow.cfg` as below.
   ```
   $ python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   BJ4_k41L1FHGVfkEWACT_HvrmI_ZOkyxT4sNPIHqG_o
   
   $ python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   qT_CoJ_Cwc7uJNZCys03y57SNhEs3y_Ch3rnEv-6gLw

   $ vim airflow.cfg
   [...]
   secret_key = qT_CoJ_Cwc7uJNZCys03y57SNhEs3y_Ch3rnEv-6gLw

   jwt_secret = BJ4_k41L1FHGVfkEWACT_HvrmI_ZOkyxT4sNPIHqG_o
   ```
   1.4 Setup airflow database
   ```
   $ airflow db migrate
   ```
   1.5 Create a user
   ```
   $ airflow users create \
    --username niket \
    --firstname Niket \
    --lastname Chavan \
    --role Admin \
    --email niket@pf9.com
   
    [...]
    Password:
    Repeat for confirmation:
    [2025-07-30T06:43:49.343+0000] {override.py:1362} INFO - Added user niket
    User "niket" created with role "Admin"
   ```

2. **Configure environment**  
   Copy `.env.template` to `.env` and fill in the required values.

3. **Configure OpenStack clouds**  
   Copy `clouds.yaml.template` to `clouds.yaml` and fill in your OpenStack cloud details.

4. **Start Airflow, approval server and the frontend portal**  
   ```
   $ sudo systemctl start airflow.service airflow-approval-server.service airflow-frontend-portal.service
   ```
5. Access the airflow using (default: localhost-ip:8080), login with the user create above and Configured SMTP in Airflow for email notifications.

   `Admin --> Connections --> Add Connection`

![alt text](<Screenshot 2025-08-14 at 17.44.44.png>)
NOTE: Add your respective SMTP host, credentials and port details. 

![alt text](<Screenshot 2025-08-14 at 17.44.58.png>)
NOTE: In the 'From email' field add the respective emaid id as per configured SMTP. It will act as the source email id.

![alt text](<Screenshot 2025-08-14 at 17.45.06.png>)

## Usage

- Visit the frontend portal (default: http://localhost-IP:5050) to request a VM.
- Admin(ADMIN_EMAIL in .env file) receives an approval email and can approve/deny via provided links.
- Upon approval, the VM is provisioned and the user is notified by email.

## Notes

- The Airflow DAG ID and other settings are controlled via the `.env` file.
- The approval server and frontend portal ports can be customized in `.env`.
- When working with ServiceNow, the frontend portal will be replaced with servicenow form.
- Setting up ServiceNow is a completely different process and is out of scope for this airflow setup.