import os
import PyPDF2
import pypdf
import pandas as pd
from docx import Document
from pathlib import Path
from typing import Dict, Any
from utils.workflow import app_workflow, initial_state
from config.settings import BASE_DIR
from .workflow import app_workflow, initial_state
from .query_handler import get_query_response

import os
import PyPDF2
import pypdf
import pandas as pd
from docx import Document
from pathlib import Path
from typing import Dict, Any
from utils.workflow import app_workflow, initial_state
from config.settings import BASE_DIR
from .workflow import app_workflow, initial_state

from docx import Document
import pandas as pd
from pathlib import Path
from typing import Dict, Any
from .workflow import app_workflow, initial_state
from .query_handler import get_query_response
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import PromptHelper

from chromadb import Client
import logging

import chromadb
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.llms import CustomLLM, CompletionResponse, CompletionResponseGen, LLMMetadata
from llama_index.core import Settings
from litellm import completion
from pathlib import Path
import os
import json
from dotenv import load_dotenv
from typing import Any
# Load environment variables
load_dotenv()
import re



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "student_uploads"






# Initialize components
embed_model = HuggingFaceEmbedding(model_name="jinaai/jina-embeddings-v2-base-en")
sentence_splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
prompt_helper = PromptHelper(
    context_window=4096,
    num_output=256,
    chunk_overlap_ratio=0.1,
    chunk_size_limit=None
)

chroma_db_path = BASE_DIR / "chroma_db"
chroma_client = chromadb.PersistentClient(path=str(chroma_db_path))
apps_collection = chroma_client.get_or_create_collection(name="applications")
apps_vector_store = ChromaVectorStore(chroma_collection=apps_collection)
apps_storage_context = StorageContext.from_defaults(vector_store=apps_vector_store)

# Initialize apps_index and apps_query_engine globally (or lazily) to reuse
apps_index = VectorStoreIndex(
    nodes=[],  # Empty initial nodes to reuse existing storage
    storage_context=apps_storage_context,
    embed_model=embed_model
)
apps_query_engine = apps_index.as_query_engine(
    embed_model=embed_model,
    prompt_helper=prompt_helper
)
#=================================================================================================================================
def extract_details_from_query_engine(email: str, query_engine) -> dict:
    details = {}
    try:
        # Age extraction using regex
        age_query = f"What is the age of the student with email {email}? Extract a number if present."
        age_response = query_engine.query(age_query)
        age_response = age_response.response if hasattr(age_response, "response") else age_response
        age_match = re.search(r"\b(\d{1,2})\b", str(age_response))
        details["age"] = int(age_match.group(1)) if age_match else None

        # PCM marks extraction
        pcm_query = f"Extract individual marks for Physics, Chemistry, and Maths (e.g., 95%, 92%, 91%) from the marksheet for {email}."
        pcm_response = query_engine.query(pcm_query)
        pcm_response = pcm_response.response if hasattr(pcm_response, "response") else pcm_response
        
        pcm_text = str(pcm_response).lower()
        marks = {}
        for subject in ["physics", "chemistry", "maths", "mathematics"]:
            match = re.search(rf"{subject}[^0-9]*?(\d{{1,3}}(?:\.\d+)?)\s*%", pcm_text)
            if match:
                key = "maths" if "math" in subject else subject
                marks[key] = float(match.group(1))
        details["pcm_aggregate"] = sum(marks.values()) / 3 if len(marks) == 3 else None

        # Income extraction
        income_query = f"Extract the parents' annual income (e.g., 120000) from any income certificate for {email}."
        income_response = query_engine.query(income_query)
        income_response = income_response.response if hasattr(income_response, "response") else income_response
        income_text = str(income_response).replace(",", "").replace("₹", "").replace("$", "").strip()
        income_match = re.search(r"\b(\d{4,9})\b", income_text)
        details["parents_income"] = int(income_match.group(1)) if income_match else None

        logger.info(f"Extracted details for {email}: {details}")
        return details
    except Exception as e:
        logger.error(f"Error querying apps_query_engine for {email}: {str(e)}")
        return {}


#=====================================================================================================================
def process_student_submission(
    name: str,
    email: str,
    query: str,
    uploaded_files: Dict[str, bytes]
) -> Dict[str, Any]:
    upload_dir = UPLOAD_DIR / email.replace("@", "_")
    upload_dir.mkdir(parents=True, exist_ok=True)

    app_files_entry = {"name": name, "email": email, "files": []}
    for filename, file_content in uploaded_files.items():
        file_path = upload_dir / filename
        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
            text = ""
            doc = Document(file_path)
            text = "\n".join([para.text.strip() for para in doc.paragraphs if para.text.strip()])

            app_files_entry["files"].append(f"{filename}: {text}")
            logger.info(f"Processed {filename} for {email}: {text[:50]}...")
        except Exception as e:
            app_files_entry["files"].append(f"{filename}: Error processing file - {str(e)}")
            logger.error(f"Failed to process {filename} for {email}: {str(e)}")

    # Index documents using SimpleDirectoryReader and SentenceSplitter
    try:
        reader = SimpleDirectoryReader(input_dir=str(upload_dir))
        documents = reader.load_data()
        logger.info(f"Loaded {len(documents)} documents from {upload_dir}")
        nodes = sentence_splitter.get_nodes_from_documents(documents)
        apps_index.insert_nodes(nodes)  # Append new nodes to the existing index
        apps_query_engine = apps_index.as_query_engine(
            embed_model=embed_model,
            prompt_helper=prompt_helper
        )  # Refresh query engine after insertion
        logger.info(f"Inserted {len(nodes)} nodes into apps_index for {email}")
    except Exception as e:
        logger.error(f"Failed to index documents for {email}: {str(e)}")

    # Extract details using the query engine
    details = extract_details_from_query_engine(email, apps_query_engine)
    app_files_entry.update(details)

    logger.info(f"App files entry: {app_files_entry}")

    new_state = initial_state.copy()
    new_state["app_files"].append(app_files_entry)
    new_state["apps_query_engine"] = apps_query_engine  # Pass updated query engine to state
    logger.info(f"New state app_files: {new_state['app_files']}")
    if query.strip():
        new_state["queries"].append({"email": email, "query": query})

    try:
        final_state = app_workflow.invoke(new_state)
        logger.info(f"Final state: {final_state}")
        query_response = get_query_response(query, email) if query.strip() else ""
    except Exception as e:
        return {
            "status": "Failed",
            "query_response": f"Error processing submission: {str(e)}",
            "final_state": None
        }

    # Persist to master_database
    tmp_path = BASE_DIR / "tmp"
    tmp_path.mkdir(exist_ok=True)
    excel_path = tmp_path / "master_database.xlsx"
    data = {
        "Name": name,
        "Email": email,
        "Files": ", ".join([f"{k}: {k}" for k in uploaded_files.keys()]),
        "Age": app_files_entry.get("age"),
        "PCM_Aggregate": app_files_entry.get("pcm_aggregate"),
        "Parents_Income": app_files_entry.get("parents_income")
    }
    df = pd.DataFrame([data])
    logger.info(f"Data to save: {data}")
    if excel_path.exists():
        existing_df = pd.read_excel(excel_path)
        df = pd.concat([existing_df, df], ignore_index=True)
    else:
        df = pd.DataFrame(columns=["Name", "Email", "Files", "Age", "PCM_Aggregate", "Parents_Income"]).append(df, ignore_index=True)
    df.to_excel(excel_path, index=False)
    logger.info(f"Saved to {excel_path}")

    return {
        "status": final_state.get("status", "Completed"),
        "query_response": query_response,
        "final_state": final_state,
        "applicant": app_files_entry
    }

