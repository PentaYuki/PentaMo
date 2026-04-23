import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.database import SessionLocal
from services.faiss_memory import get_faiss_memory
from services.llm_client import set_review_llm
from db.models import FAISSPendingReview

def run_test():
    print("STEP: Init DB")
    db = SessionLocal()
    print("STEP: Get FAISS")
    memory = get_faiss_memory()
    print("STEP: Set LLM")
    set_review_llm("gemini")
    print("STEP: Run gate_and_add")
    res = memory.gate_and_add("test q", "test a", mode="consultant", db_session=db)
    print("RESULT:", res)

if __name__ == "__main__":
    run_test()
