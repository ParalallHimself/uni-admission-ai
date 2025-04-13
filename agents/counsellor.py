# agents/counsellor.py

def unwrap_response(resp):
    while hasattr(resp, "response"):
        resp = resp.response
    return str(resp).strip()



from typing import Dict, Any
import smtplib
from email.mime.text import MIMEText
from config.settings import static_query_engine, GMAIL_USER, GMAIL_PASS

from typing import Dict, Any
import smtplib
from email.mime.text import MIMEText
from config.settings import GMAIL_USER, GMAIL_PASS
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def counsellor_run(state: Dict[str, Any]) -> Dict[str, Any]:
    communications = state["communications"].copy()
    report = "Counsellor Report:\n"
    emails_sent = 0

    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    # Access the query engine from the state
    apps_query_engine = state.get("apps_query_engine")
    for candidate in state["shortlisted_apps"]:
        name = candidate["name"]
        email = candidate["email"]
        subject = "Admission Offer from University Admission Cell"
        body = f"""
        Dear {name},

        Congratulations! You have been shortlisted for admission to our university.
        Details:
        - Educational Qualification: {candidate["educational_qualification"]}
        - Exam Score: {candidate["exam_score"]}
        - Key Highlights: {candidate["key_highlights"]}

        Please reply to this email to confirm your acceptance.

        Best regards,
        University Admission Cell
        """

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = email

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(GMAIL_USER, GMAIL_PASS)
                server.send_message(msg)
            communications.append({"to": email, "subject": subject, "status": "Sent"})
            emails_sent += 1
            report += f"- Email sent to {name} ({email})\n"
        except Exception as e:
            communications.append({"to": email, "subject": subject, "status": f"Failed: {str(e)}"})
            report += f"- Failed to send email to {name} ({email}): {str(e)}\n"

    if state["queries"]:
        report += "\nStudent Queries:\n"
        for query in state["queries"]:
            email = query.get("email", "Unknown")
            question = query.get("query", "No question provided")
            try:
                answer = (
                    apps_query_engine.query(question) if apps_query_engine 
                    else "No dynamic response available (query engine unavailable)"
                )
                answer = unwrap_response(answer)
            except Exception as e:
                answer = f"Error answering query: {str(e)}"
            report += f"- Query from {email}: '{question}'\n  Response: {answer}\n"

    total_applicants = len(state["app_files"])
    report += f"\nSummary:\n- Total applicants: {total_applicants}\n- Emails sent: {emails_sent}\n- Shortlisted candidates database:\n"
    for candidate in state["shortlisted_apps"]:
        report += f"  - {candidate['name']}: {candidate}\n"

    return {
        **state,
        "communications": communications,
        "reports": {**state["reports"], "counsellor": report},
        "status": "Counselled"
    }