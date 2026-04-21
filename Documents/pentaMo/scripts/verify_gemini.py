import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from services.llm_client import llm_client
import logging

# Configure logging to see output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyGemini")

def verify_gemini():
    print("\n--- PENTAMO GEMINI VERIFICATION ---")
    print(f"Provider: {settings.llm_provider}")
    print(f"Model: {settings.gemini_model_name}")
    print(f"API Key present: {'Yes' if settings.google_api_key else 'No'}")
    
    if not settings.google_api_key:
        print("ERROR: GOOGLE_API_KEY is missing in settings.")
        return

    # test 1: Simple generation
    print("\n[Test 1] Simple Generation...")
    prompt = "Chào bạn, hãy giới thiệu ngắn gọn về bản thân bạn là ai (trong vai tư vấn viên xe máy PentaMo)."
    response = llm_client.generate(prompt)
    if response:
        print(f"SUCCESS! Response:\n{response}")
    else:
        print("FAILED: No response generated.")

    # test 2: JSON generation
    print("\n[Test 2] JSON Extraction...")
    prompt = "Tôi muốn tìm xe Honda Vision đời 2022 ở Hà Nội tầm giá 30 triệu. Hãy trích xuất thông tin thành JSON."
    json_res = llm_client.generate_json(prompt)
    if json_res:
        print(f"SUCCESS! JSON Result:\n{json_res}")
    else:
        print("FAILED: Could not parse JSON.")

    print("\n-----------------------------------\n")

if __name__ == "__main__":
    verify_gemini()
