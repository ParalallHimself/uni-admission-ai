# agents/loan_agent.py
from typing import Dict, Any
import smtplib
from email.mime.text import MIMEText
from config.settings import static_query_engine, llm_call, GMAIL_USER, GMAIL_PASS


from typing import Dict, Any
import smtplib
from email.mime.text import MIMEText
from config.settings import GMAIL_USER, GMAIL_PASS
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def loan_agent_run(state: Dict[str, Any]) -> Dict[str, Any]:
    loan_requests = state["loan_requests"].copy()
    communications = state["communications"].copy()
    report = "Loan Agent Report:\n"
    emails_sent = 0

    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    # Access the query engines from the state
    apps_query_engine = state.get("apps_query_engine")
    # Use static_query_engine for threshold from eligibility criteria
    try:
        threshold_response = static_query_engine.query("What is the annual income threshold for loan eligibility from eligibility criteria?")
        threshold_response = threshold_response.response if hasattr(threshold_response, "response") else threshold_response
        income_threshold = 250000  # Default value
        for word in str(threshold_response).split():
            if word.replace(",", "").replace("$", "").isdigit():
                income_threshold = int(word.replace(",", "").replace("$", ""))
                break
        report += f"Income threshold: ${income_threshold}\n"
    except Exception as e:
        report += f"Warning: Using default threshold ${income_threshold}. Error: {str(e)}\n"

    for app in state["app_files"]:
        name = app.get("name", "Unknown")
        email = app.get("email", "Unknown")
        files = app.get("files", [])
        shortlisted = any(s["name"] == name and s["email"] == email for s in state["shortlisted_apps"])

        if not shortlisted:
            report += f"- {name} ({email}): Not shortlisted, skipping loan processing\n"
            continue  # Skip to next applicant if not shortlisted

        # Proceed only if shortlisted
        if any("income certificate" in file.lower() for file in files) and apps_query_engine:
            prompt = f"Extract the annual income from the income certificate content for {name} ({email}). Respond with the numerical income value (e.g., 30000) or 'Unknown' if not found."
            income_str = apps_query_engine.query(prompt)
            income_str = income_str.response if hasattr(income_str, "response") else income_str 
            try:
                parents_income = int(income_str.replace(",", "").replace("$", ""))
            except ValueError:
                parents_income = None
                logger.warning(f"Could not parse income for {name} ({email}), using 'Unknown'")
        else:
            parents_income = None
            logger.warning(f"No income certificate or apps_query_engine for {name} ({email}), using 'Unknown'")

        if parents_income is not None and parents_income < income_threshold:
            loan_amount = min(10000, income_threshold - parents_income)
            status = "Approved"
            report += f"- {name} ({email}): Loan Approved (Income: ${parents_income}, Amount: ${loan_amount})\n"
        else:
            status = "Rejected"
            reason = f"Income (${parents_income}) exceeds threshold" if parents_income else "Income not found or not below threshold"
            loan_amount = 0
            report += f"- {name} ({email}): Loan Rejected ({reason})\n"

        loan_requests.append({
            "name": name,
            "email": email,
            "parents_income": parents_income,
            "loan_amount": loan_amount,
            "status": status
        })

        subject = f"Loan Application Status - {status}"
        body = f"""
        Dear {name},

        Your loan application has been processed.
        Status: {status}
        {f'Loan Amount: ${loan_amount}' if status == 'Approved' else f'Reason: {reason}'}

        Regards,
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
            report += f"  - Email sent\n"
        except Exception as e:
            communications.append({"to": email, "subject": subject, "status": f"Failed: {str(e)}"})
            report += f"  - Failed to send email: {str(e)}\n"

    report += f"\nSummary:\n- Loan emails sent: {emails_sent}\n"
    return {
        **state,
        "loan_requests": loan_requests,
        "communications": communications,
        "reports": {**state["reports"], "loan_agent": report},
        "status": "Loans Processed"
    }
