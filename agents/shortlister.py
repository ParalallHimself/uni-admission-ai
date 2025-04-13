# agents/shortlister.py
from typing import Dict, Any
from config.settings import static_query_engine, llm_call

import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def shortlister_run(state: Dict[str, Any]) -> Dict[str, Any]:
    shortlisted_apps = []
    report = "Shortlisting Report:\n"

    # Access the query engine from the state
    apps_query_engine = state.get("apps_query_engine")
    try:
        # Use static_query_engine for static eligibility criteria and seats
        criteria_response = static_query_engine.query("What are the eligibility criteria for admission?")
        criteria_response = criteria_response.response if hasattr(criteria_response, "response") else criteria_response
        seats_response = static_query_engine.query("How many seats are available in total across all branches?")
        seats_response = seats_response.response if hasattr(seats_response, "response") else seats_response
        report += f"Criteria: {criteria_response}\nSeats: {seats_response}\n"
        max_seats = None
        for word in str(seats_response).split():
            if word.isdigit():
                max_seats = int(word)
                break
        max_seats = max_seats or 2
    except Exception as e:
        criteria_default = "All required documents (resume, Marksheet, Income Certificate(only for loan request)) must be present"
        max_seats = 2
        report += f"Error fetching criteria/seats: {str(e)}. Using default: {criteria_default}, Seats: {max_seats}\n"

    eligible_candidates = [app for app in state["validated_apps"] if app["is_valid"]]
    for i, app in enumerate(state["validated_apps"]):
        name = app["name"]
        email = app["email"]
        file_content = " ".join(state["app_files"][i].get("files", ["No content"]))

        prompt = f"""
        Given the application content for {name} ({email}):
        "{file_content}"

        Extract or infer:
        - Age
        - Educational Qualification
        - Exam Score
        - Phone Number
        - Key Highlights
        If not found, provide reasonable defaults or 'Unknown'.
        Respond in this format:
        - Age: [value]
        - Educational Qualification: [value]
        - Exam Score: [value]
        - Phone Number: [value]
        - Key Highlights: [value]
        """
        # Use only apps_query_engine, with fallback to default values if unavailable
        response = apps_query_engine.query(prompt) if apps_query_engine else None
        response = response.response if hasattr(response, "response") else response
        if not response:
            logger.warning(f"No apps_query_engine or query failed for {name} ({email}), using default values")
            response = "\n- Age: Unknown\n- Educational Qualification: Unknown\n- Exam Score: Unknown\n- Phone Number: Unknown\n- Key Highlights: None"

        details = {"Age": "Unknown", "Educational Qualification": "Unknown", "Exam Score": "Unknown",
                   "Phone Number": "Unknown", "Key Highlights": "None"}
        for line in response.split("\n"):
            if ": " in line:
                key, value = line.split(": ", 1)
                key = key.strip("- ").strip()
                if key in details:
                    details[key] = value.strip()

        if app["is_valid"] and len(shortlisted_apps) < max_seats:
            shortlisted_app = {
                "name": name,
                "email": email,
                "age": details["Age"],
                "educational_qualification": details["Educational Qualification"],
                "exam_score": details["Exam Score"],
                "phone_number": details["Phone Number"],
                "key_highlights": details["Key Highlights"]
            }
            shortlisted_apps.append(shortlisted_app)
            report += f"- {name} ({email}): Shortlisted\n  Details: {response}\n"
        else:
            reason = "Seats full" if app["is_valid"] else "Missing required documents"
            report += f"- {name} ({email}): Not shortlisted ({reason})\n  Details: {response}\n"

    if not eligible_candidates:
        report += "No candidates met the eligibility criteria.\n"

    return {
        **state,
        "shortlisted_apps": shortlisted_apps,
        "reports": {**state["reports"], "shortlister": report},
        "status": "Shortlisted"
    }
    
    