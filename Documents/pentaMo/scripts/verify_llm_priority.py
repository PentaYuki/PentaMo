import sys
import os
import logging

# Setup path
sys.path.append(os.getcwd())

from services.llm_client import llm_client
from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_LLM")

def test_llm_priority():
    print("\n--- LLM PRIORITY & FALLBACK TEST ---")
    print(f"Preferred Provider: {settings.llm_provider}")
    
    # 1. Test normal generation (tries primary first)
    print("\n1. Testing Primary Provider Generation...")
    try:
        response = llm_client.generate("Xin chào, bạn là ai?")
        print(f"Response: {response}")
        print("✓ Generation test completed.")
    except Exception as e:
        print(f"❌ Generation test failed: {e}")

    # 2. Test JSON generation
    print("\n2. Testing JSON Generation...")
    try:
        json_resp = llm_client.generate_json("Trả về JSON: {'test': 'success'}")
        print(f"JSON Response: {json_resp}")
        print("✓ JSON test completed.")
    except Exception as e:
        print(f"❌ JSON test failed: {e}")

    print("\n--- TEST COMPLETED ---")

if __name__ == "__main__":
    test_llm_priority()
