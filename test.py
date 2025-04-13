
from utils.file_processing import process_student_submission  # replace with actual module name
import os

from config.settings import static_query_engine
from utils.query_handler import get_query_response 

# Mock uploaded file content
sample_text = b"Name: John Doe\nEmail: john@example.com\nDegree: B.Tech"
uploaded_files = {
    "resume.txt": sample_text,
    "marksheet.txt": b"CGPA: 9.2\nYear: 2023",
}

# Dummy input
test_name = "John Doe"
test_email = "john.doe@example.com"
test_query = "What is the eligibility criteria?"

# Run the function
result = process_student_submission(
    name=test_name,
    email=test_email,
    query=test_query,
    uploaded_files=uploaded_files
)

# Pretty print the output
import json
print(json.dumps(result, indent=4, default=str))