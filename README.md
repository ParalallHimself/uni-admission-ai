# University Admission Cell

A Streamlit-based application for managing university admissions with a multi-agent system. Students can upload documents (PDF, DOCX, TXT) and submit queries, while admins view reports and download a master database.

## Features
- **Student Interface**: Upload documents, submit queries, view query responses.
- **Admin Interface**: View agent reports, master database, Excel link (password: `admin123`).
- **Agents**: Document checker, shortlister, counsellor, loan agent, admission officer.
- **Backend**: Uses Gemini LLM, ChromaDB, Google Drive API.

## Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/UniversityAdmissionCell.git
   cd UniversityAdmissionCell
   ```

2. **Install the dependencies**
    ```bash
    pip install -r requirements.txt
    ```
