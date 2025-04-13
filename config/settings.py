# config/settings.py
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

# Project directory
BASE_DIR = Path(__file__).parent.parent

# Credentials
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERVICE_ACCOUNT_JSON = json.loads(os.getenv("SERVICE_ACCOUNT_JSON"))

# ChromaDB setup
chroma_db_path = BASE_DIR / "chroma_db"
chroma_client = chromadb.PersistentClient(path=str(chroma_db_path))
static_collection = chroma_client.get_or_create_collection(name="static_docs")


# Load static documents
static_dir = BASE_DIR / "static_docs"
reader = SimpleDirectoryReader(input_dir=static_dir)
documents = reader.load_data()
#print(documents)



splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=500)
nodes = splitter.get_nodes_from_documents(documents)



from llama_index.core.settings import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import VectorStoreIndex

# Define the embedding model
embed_model = HuggingFaceEmbedding(model_name="jinaai/jina-embeddings-v2-base-en")

# Set the global settings (or pass explicitly later if needed)
Settings.embed_model = embed_model

from llama_index.core.llms import CustomLLM, CompletionResponse, CompletionResponseGen, LLMMetadata
from llama_index.core.llms.callbacks import llm_completion_callback



SYSTEM_PROMPT = """
You are a knowledgeable and helpful university admissions assistant.

Your job is to:
- Answer student queries using the provided university documents as context.
- Always provide complete, detailed, and fact-based answers.
- Avoid vague or partial responses. Never stop after an introductory phrase.

Guidelines:
- Use bullet points or structured paragraphs for clarity.
- Include specific numbers like fees, seats, durations, or deadlines if present.
- Extract all relevant details from the documents.
- If information is not explicitly available, make logical inferences or generate helpful content on your own.
- Never say "The information is not available." Be proactive and constructive.

Answering Strategy:
- First, identify the student’s intent behind the query.
- Then, search through the provided documents and extract all relevant facts.
- Finally, compile those facts into a well-structured response.

You must take at least 3 reasoning steps before answering. Do not answer immediately. Think step-by-step.

Tone:
- Polite, clear, professional, and student-friendly.

Your goal is to ensure the student fully understands everything relevant to their question.
"""


# Custom LLM class to integrate LiteLLMModel with llama-index
class GeminiLLM(CustomLLM):
    context_window: int = 8192
    num_output: int = 5000
    model_name: str = "gemini/gemini-2.0-flash"

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=self.context_window,
            num_output=self.num_output,
            model_name=self.model_name,
        )

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        from llama_index.core.utils import get_tokenizer
        tokenizer = get_tokenizer()

        # Get token count of the prompt
        token_count = len(tokenizer(prompt))

        # Give ample space for output while ensuring not to exceed context window
        available_output = self.context_window - token_count
        safe_output_limit = max(min(self.num_output, available_output), 1000)  # Always allow at least 1000 tokens

        # Debug info
        print(f"\n--- LLM Prompt Length: {token_count} tokens")
        print(f"--- Max Output Allowed: {safe_output_limit} tokens")
        print(f"--- Prompt Preview:\n{prompt[:500]}...\n")

        response = completion(
            model=self.model_name,
            messages=[{"content": prompt, "role": "user"}],
            api_key=GEMINI_API_KEY,
            max_tokens=safe_output_limit
        )

        # Log full raw response (can be very long)
        raw_output = response.choices[0].message.content
        print(f"\n--- LLM Raw Output:\n{raw_output[:1000]}...\n")

        return CompletionResponse(text=raw_output)

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        response = llm_call(prompt)
        for char in response:
            yield CompletionResponse(text=char, delta=char)

# Set global LLM and embedding model in Settings
Settings.llm = GeminiLLM()

# LLM call function
def llm_call(prompt: str) -> str:
    response = completion(
        model="gemini/gemini-2.0-flash",
        messages=[{"content": prompt, "role": "user"}],
        api_key=GEMINI_API_KEY,
        max_tokens=8192
    )
    return response.choices[0].message.content

# Vector store setup
static_vector_store = ChromaVectorStore(chroma_collection=static_collection)
storage_context = StorageContext.from_defaults(vector_store=static_vector_store)

from llama_index.core.indices.prompt_helper import PromptHelper

# Adjust the prompt helper's parameters
new_prompt_helper = PromptHelper(
    context_window=8192,
    num_output=5000,
    chunk_size_limit=1024
)

# create the index ====================================================
static_index = VectorStoreIndex(
    nodes=nodes,
    storage_context=storage_context,
    show_progress=True,
    prompt_helper=new_prompt_helper # Use the custom prompt helper
)

# persist Chroma DB=================================================
static_index.storage_context.persist()



from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.prompts import PromptTemplate

# Custom prompt template
from llama_index.core.prompts import PromptTemplate

custom_prompt = PromptTemplate(
    "You are a helpful university admissions assistant. You are answering a student's question using the information provided in the documents below.\n\n"
    "Your job is to extract all relevant facts and present them in a clear, complete, and detailed way.\n\n"
    "Guidelines:\n"
    "- use information from the documents (context_str).\n"
    "- Provide complete information — do not stop after an introductory phrase.\n"
    "- Use bullet points or paragraphs for clarity.\n"
    "- Always include numbers (e.g., fees, seats) if available.\n"
    "- If the documents do not contain the answer, try to generate on your own. Never say: 'The information is not available in the university's documents.'\n\n"
    "Context:\n{context_str}\n\n"
    "Student Query: {query_str}\n\n"
    "Final Answer:"
)



static_query_engine = static_index.as_query_engine(
    text_qa_template=custom_prompt,
    similarity_top_k=10  # or 8 depending on your document size
)

#=========================================================================================================
apps_collection = chroma_client.get_or_create_collection(name="applications")
UPLOAD_DIR = BASE_DIR / "student_uploads"



apps_vector_store = ChromaVectorStore(chroma_collection=apps_collection)
apps_storage_context = StorageContext.from_defaults(vector_store=apps_vector_store)

apps_index = VectorStoreIndex(
    nodes=nodes,
    storage_context=apps_storage_context,
    embed_model=embed_model,   
)

apps_query_engine = apps_index.as_query_engine(
    embed_model=embed_model,
    prompt_helper=new_prompt_helper
)


__all__ = ["static_query_engine"]