# app.py
import streamlit as st
import os
from pathlib import Path
from typing import Dict, Any
from utils.file_processing import process_student_submission
from utils.workflow import initial_state, app_workflow
import pandas as pd
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project directory
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "student_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

def main():
    st.set_page_config(page_title="University Admission Cell", layout="wide")


    # Initialize session state
    if "app_state" not in st.session_state:
        st.session_state.app_state = initial_state.copy()
        # Ensure "app_files" is initialized
        st.session_state.app_state["app_files"] = []
        
    # Sidebar for user selection
    user_type = st.sidebar.selectbox("Select User Type", ["Student", "University Admin"])


    if user_type == "Student":
        st.header("Student Admission Portal")
        st.write("Upload your documents and ask any queries about admission.")

        with st.form(key="student_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            query = st.text_area("Query (Optional)", placeholder="E.g., What are the number of seats?")
            uploaded_files = st.file_uploader(
                "Upload Documents (PDF, DOCX, TXT)",
                accept_multiple_files=True,
                type=["pdf", "docx", "txt"]
            )
            submit_button = st.form_submit_button("Submit")

            if submit_button:
                if not name or not email:
                    st.error("Please provide name and email.")
                elif not uploaded_files:
                    st.error("Please upload at least one document.")
                else:
                    # Prepare uploaded files
                    files_dict = {file.name: file.read() for file in uploaded_files}
                    result = process_student_submission(name, email, query, files_dict)

                    if result.get("final_state"):
                        st.session_state.app_state = result["final_state"]
                    else:
                        st.warning("Using previous state due to processing error.")

                    # Avoid duplicate app_file entry
                    if result.get("applicant"):
                        st.session_state.app_state["app_files"].append(result["applicant"])

                    st.success("Document upload successful.")

                    # Display query response
                    if query.strip():
                        st.markdown("**University Response:**")
                        full_response = result.get("query_response", "No response available.")
                        st.markdown(
                            f"<div style='white-space: pre-wrap; font-size: 16px; line-height: 1.6'>{full_response}</div>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.write("No query submitted.")
                    

    elif user_type == "University Admin":
        st.header("University Admin Dashboard")
        st.write("View admission reports and master database.")

        # Simple password protection
        password = st.text_input("Enter Admin Password", type="password")
        correct_password = "admin123"  # Replace with secure method in production

        if password == correct_password:
            try:
                latest_state = app_workflow.invoke(st.session_state.app_state)
                st.subheader("Admission Reports")
                for agent, report in latest_state["reports"].items():
                    with st.expander(f"{agent.capitalize()} Report"):
                        st.text(report)

                st.subheader("Master Database")
                if latest_state["master_database"]:
                    df = pd.DataFrame(latest_state["master_database"])
                    st.dataframe(df)
                else:
                    st.write("No data in master database.")

                st.subheader("Excel Download Link")
                excel_link = latest_state.get("excel_link", "")
                if excel_link:
                    st.markdown(f"[Download Master Database]({excel_link})")
                else:
                    st.write("Excel file not generated.")

            except Exception as e:
                st.error(f"Error fetching reports: {str(e)}")
        elif password:
            st.error("Incorrect password.")

if __name__ == "__main__":
    main()
    
