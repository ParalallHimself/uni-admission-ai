# agents/doc_checker.py
from typing import Dict, Any
from config.settings import llm_call

from typing import Dict, Any
from config.settings import apps_query_engine
import logging

    
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def doc_checker_run(state: Dict[str, Any]) -> Dict[str, Any]:
    base_required_docs = ["resume", "marksheet"]
    optional_docs = ["income certificate"]
    validated_apps: List[Dict[str, Any]] = []
    report = "📄 Document Checker Report:\n"

    apps_query_engine = state.get("apps_query_engine")
    if not apps_query_engine:
        logger.warning("No apps_query_engine found in state. Skipping document check.")
        return state

    for app in state.get("app_files", []):
        name = app.get("name", "Unknown")
        email = app.get("email", "Unknown")
        file_texts = app.get("files", [])
        present = []
        missing = []

        # Determine if loan is requested based on file content
        loan_requested = any(
            "loan" in file.lower() or "income certificate" in file.lower() for file in file_texts
        )

        # Determine the list of docs to check for this applicant
        docs_to_check = base_required_docs + optional_docs if loan_requested else base_required_docs

        for doc in docs_to_check:
            doc_query = (
                f"Check if the submitted documents for student {name} ({email}) include a valid {doc} based on content. "
                f"For example, a marksheet includes subjects and marks (like Physics, Chemistry, Maths); "
                f"an income certificate includes income amount, guardian name, and certifying officer; "
                f"a resume includes education, skills, and contact information. "
                f"Reply with 'Yes' if found, else 'No'. Also include a short reason."
            )
            try:
                response = apps_query_engine.query(doc_query)
                response = response.response if hasattr(response, "response") else response
                result = str(response).strip().lower()
                logger.info(f"Doc check for {doc} in {name}: {result}")

                if "yes" in result:
                    present.append(doc)
                else:
                    # fallback check via filename
                    if any(doc in file.lower() for file in file_texts):
                        logger.warning(f"Fallback: '{doc}' not found by LLM but exists in file names.")
                        present.append(doc)
                    else:
                        missing.append(doc)
            except Exception as e:
                logger.error(f"Error querying for {doc} in {name}: {str(e)}")
                missing.append(doc)

        validated_app = {
            "name": name,
            "email": email,
            "present_docs": present,
            "missing_docs": missing,
            "is_valid": len(missing) == 0
        }
        validated_apps.append(validated_app)

        report += (
            f"\n- {name} ({email}):\n"
            f"  ✅ Present: {present}\n"
            f"  ❌ Missing: {missing}\n"
        )

    return {
        **state,
        "validated_apps": validated_apps,
        "reports": {**state.get("reports", {}), "doc_checker": report},
        "status": "Docs Checked"
    }
