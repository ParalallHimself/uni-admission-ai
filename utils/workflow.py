# utils/workflow.py

from langgraph.graph import StateGraph, END
from typing import Dict, Any, Optional
from agents.doc_checker import doc_checker_run
from agents.shortlister import shortlister_run
from agents.counsellor import counsellor_run
from agents.loan_agent import loan_agent_run
from agents.admission_officer import admission_officer_run

from pathlib import Path


from langgraph.graph import StateGraph, END
from typing import Dict, Any
from agents.doc_checker import doc_checker_run
from agents.shortlister import shortlister_run
from agents.counsellor import counsellor_run
from agents.loan_agent import loan_agent_run
from agents.admission_officer import admission_officer_run

from langgraph.graph import StateGraph, END
from typing import Dict, Any, List
import pandas as pd
from pathlib import Path


from langgraph.graph import StateGraph, END
from typing import Dict, Any
from agents.doc_checker import doc_checker_run
from agents.shortlister import shortlister_run
from agents.counsellor import counsellor_run
from agents.loan_agent import loan_agent_run
from agents.admission_officer import admission_officer_run
from pathlib import Path


AdmissionState = Dict[str, Any]

initial_state: AdmissionState = {
    "app_files": [],
    "validated_apps": [],
    "shortlisted_apps": [],
    "communications": [],
    "loan_requests": [],
    "queries": [],
    "reports": {},
    "master_database": [],
    "excel_link": "",
    "status": "Initialized",
    "apps_query_engine": None
}

BASE_DIR = Path(__file__).parent.parent

def doc_checker_node(state: AdmissionState) -> AdmissionState:
    return doc_checker_run(state)

def shortlist_node(state: AdmissionState) -> AdmissionState:
    return shortlister_run(state)

def counsellor_node(state: AdmissionState) -> AdmissionState:
    return counsellor_run(state)

def loan_agent_node(state: AdmissionState) -> AdmissionState:
    return loan_agent_run(state)

def admission_officer_node(state: AdmissionState) -> AdmissionState:
    return admission_officer_run(state)

workflow = StateGraph(AdmissionState)
workflow.add_node("doc_checker", doc_checker_node)
workflow.add_node("shortlister", shortlist_node)
workflow.add_node("counsellor", counsellor_node)
workflow.add_node("loan_agent", loan_agent_node)
workflow.add_node("admission_officer", admission_officer_node)

workflow.add_edge("doc_checker", "shortlister")
workflow.add_edge("shortlister", "counsellor")
workflow.add_edge("counsellor", "loan_agent")
workflow.add_edge("loan_agent", "admission_officer")
workflow.add_edge("admission_officer", END)

workflow.set_entry_point("doc_checker")
app_workflow = workflow.compile()