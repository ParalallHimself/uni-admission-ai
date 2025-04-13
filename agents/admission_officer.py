# agents/admission_officer.py
from typing import Dict, Any
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config.settings import SERVICE_ACCOUNT_JSON
from pathlib import Path

# Project directory
BASE_DIR = Path(__file__).parent.parent
TMP_DIR = BASE_DIR / "tmp"
TMP_DIR.mkdir(exist_ok=True)

from typing import Dict, Any
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config.settings import SERVICE_ACCOUNT_JSON
from pathlib import Path
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Project directory
BASE_DIR = Path(__file__).parent.parent
TMP_DIR = BASE_DIR / "tmp"
TMP_DIR.mkdir(exist_ok=True)

def admission_officer_run(state: Dict[str, Any]) -> Dict[str, Any]:
    report = "Admission Officer Report:\n\nProceedings Summary:\n"

    # Access the query engine from the state
    apps_query_engine = state.get("apps_query_engine")
    for agent, agent_report in state["reports"].items():
        report += f"### {agent.capitalize()} Report:\n{agent_report}\n\n"

    master_database = []
    for app in state["app_files"]:
        entry = {"name": app["name"], "email": app["email"], "files": "; ".join(app["files"])}
        validated = next((v for v in state["validated_apps"] if v["name"] == app["name"]), {})
        entry.update({
            "present_docs": "; ".join(validated.get("present_docs", [])),
            "missing_docs": "; ".join(validated.get("missing_docs", [])),
            "is_valid": validated.get("is_valid", False),
            "institute_verified": validated.get("institute_verified", "No")
        })
        shortlisted = next((s for s in state["shortlisted_apps"] if s["name"] == app["name"]), {})
        entry.update({
            "shortlisted": bool(shortlisted),
            "age": shortlisted.get("age", "Unknown"),
            "educational_qualification": shortlisted.get("educational_qualification", "Unknown"),
            "exam_score": shortlisted.get("exam_score", "Unknown"),
            "phone_number": shortlisted.get("phone_number", "Unknown"),
            "key_highlights": shortlisted.get("key_highlights", "None")
        })
        loan = next((l for l in state["loan_requests"] if l["name"] == app["name"]), {})
        entry.update({
            "loan_status": loan.get("status", "Not Applied"),
            "parents_income": loan.get("parents_income", "N/A"),
            "loan_amount": loan.get("loan_amount", 0)
        })
        comms = [c for c in state["communications"] if c["to"] == app["email"]]
        entry["communications"] = "; ".join([f"{c['subject']} ({c['status']})" for c in comms])
        queries = [q for q in state["queries"] if q["email"] == app["email"]]
        entry["queries"] = "; ".join([q["query"] for q in queries]) if queries else "None"
        master_database.append(entry)

    sample_query = "How many students were shortlisted?"
    try:
        shortlisted_count = len(state["shortlisted_apps"])
        if apps_query_engine:
            dynamic_response = apps_query_engine.query(sample_query)
            dynamic_response = dynamic_response.response if hasattr(dynamic_response, "response") else dynamic_response
            
            report += f"Sample Query: '{sample_query}'\nDynamic Response: {dynamic_response}\nCalculated Response: {shortlisted_count} students were shortlisted.\n"
        else:
            report += f"Sample Query: '{sample_query}'\nResponse: {shortlisted_count} students were shortlisted (no dynamic query engine).\n"
    except Exception as e:
        report += f"Sample Query: '{sample_query}'\nError: {str(e)}\nCalculated Response: {shortlisted_count} students were shortlisted.\n"

    try:
        df = pd.DataFrame(master_database)
        excel_path = TMP_DIR / "master_database.xlsx"
        df.to_excel(excel_path, index=False)

        credentials = service_account.Credentials.from_service_account_info(
            SERVICE_ACCOUNT_JSON, scopes=['https://www.googleapis.com/auth/drive']
        )
        drive_service = build('drive', 'v3', credentials=credentials)

        folder_name = "UniversityAdmissionCell"
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        folder_response = drive_service.files().list(q=query, fields="files(id, name)").execute()
        folders = folder_response.get('files', [])
        if not folders:
            raise Exception(f"Folder '{folder_name}' not found.")
        folder_id = folders[0]['id']

        file_query = f"name = 'master_database.xlsx' and '{folder_id}' in parents and trashed = false"
        file_response = drive_service.files().list(q=file_query, fields="files(id, name)").execute()
        files = file_response.get('files', [])

        if files:
            file_id = files[0]['id']
            media = MediaFileUpload(excel_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            drive_service.files().update(fileId=file_id, media_body=media).execute()
            report += "Updated existing master_database.xlsx in Google Drive.\n"
        else:
            file_metadata = {'name': 'master_database.xlsx', 'parents': [folder_id]}
            media = MediaFileUpload(excel_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            file_id = file.get('id')
            report += "Created new master_database.xlsx in Google Drive.\n"

        drive_service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        excel_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        report += f"Master Database exported to Excel: {excel_link}\n"
    except Exception as e:
        excel_link = ""
        report += f"\nError uploading/updating Excel: {str(e)}\n"

    return {
        **state,
        "master_database": master_database,
        "reports": {**state["reports"], "master": report},
        "excel_link": excel_link,
        "status": "Completed"
    }
    
    