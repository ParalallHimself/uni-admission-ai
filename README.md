# 🎓 University Admission Cell

A **Streamlit-based AI-powered system** for automating and managing university admissions through a **multi-agent framework**. Students can upload application documents and ask questions, while admins review reports, make decisions, and download the final admissions database.

---
## 🚀 Features

- 🔹 **Student Interface**  
  Upload documents (PDF, DOCX, TXT), ask questions, and receive intelligent responses.

- 🔹 **Admin Interface**  
  View detailed agent reports, monitor shortlisted candidates, and export the master admissions database.  
  *(Excel file download password: `admin123`)*

- 🤖 **AI Agents**  
  - Document Validator  
  - Shortlister  
  - Career Counsellor  
  - Loan Eligibility Checker  
  - Admission Officer  

- ⚙️ **Tech Stack**  
  - Gemini LLM via LiteLLM  
  - ChromaDB for document indexing  
  - Streamlit for frontend  
  - Google Drive API for export

---

## 🛠️ Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/21spl/uni-admission-ai.git
   cd uni-admission-ai
   ```
2. **Install Dependencies**
   Make sure you have Python 3.9+ installed.
   ```bash
   pip install -r requirements.txt
   ```
---

## ▶️ Run the App

Start the Streamlit application:

```bash
streamlit run app.py
```

The app will open in your default browser at [http://localhost:8501](http://localhost:8501)

---

