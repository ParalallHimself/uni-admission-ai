from config.settings import static_query_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_query_response(query: str, email: str) -> str:
    """
    Generate a response to a student query using static_query_engine.
    """
    try:
        if not query or not query.strip():
            return "No query provided."
        # Define university-related keywords
        university_queries = ["fees structure", "eligibility criteria", "number of seats", "fee", "eligibility"]
        question = query.lower()
        if any(keyword in question for keyword in university_queries):
            response = static_query_engine.query(question)
            response = response.response if hasattr(response, "response") else response
        else:
            response = static_query_engine.query(question)
            response = response.response if hasattr(response, "response") else response

        response = response.strip()  # ✅ KEEP full response

        if not response or "does not contain" in response.lower():
            response = "Please contact the university admin for this information."

        logger.info(f"Query from {email}: {query} -> Response: {response}")
        return response

    except Exception as e:
        logger.error(f"Error processing query from {email}: {str(e)}")
        return f"Error processing query: {str(e)}"
