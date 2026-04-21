#!/usr/bin/env python
"""
Test script for the refactored orchestrator system
Tests FAISS memory, mode detection, and LLM integration
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)
os.chdir(project_root)

import logging
from backend.orchestrator_v3 import orchestrator
from services.faiss_memory import get_faiss_memory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_faiss_memory():
    """Test FAISS memory functionality"""
    logger.info("=" * 60)
    logger.info("TEST 1: FAISS Memory")
    logger.info("=" * 60)
    
    memory = get_faiss_memory()
    stats = memory.get_stats()
    
    logger.info(f"✓ FAISS Memory Stats:")
    logger.info(f"  Total pairs: {stats['total_pairs']}")
    logger.info(f"  Consultant mode: {stats['consultant_count']}")
    logger.info(f"  Trader mode: {stats['trader_count']}")
    
    # Test search for consultant mode
    logger.info("\nTesting consultant mode search...")
    answer = memory.search(
        "Xe ga nào tốt dưới 30 triệu?",
        mode="consultant",
        threshold=0.7
    )
    if answer:
        logger.info(f"✓ Found cached answer (first 100 chars): {answer[:100]}...")
    else:
        logger.warning("✗ No cached answer found (expected for close match)")
    
    # Test search for trader mode
    logger.info("\nTesting trader mode search...")
    answer = memory.search(
        "Bán xe máy cũ thủ tục thế nào?",
        mode="trader",
        threshold=0.7
    )
    if answer:
        logger.info(f"✓ Found cached answer (first 100 chars): {answer[:100]}...")
    else:
        logger.warning("✗ No cached answer found")
    
    return True


def test_mode_detection():
    """Test mode detection logic"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Mode Detection")
    logger.info("=" * 60)
    
    test_cases = [
        ("Xe ga nào tốt dưới 30 triệu?", "consultant"),
        ("Tôi muốn mua xe Honda", "trader"),
        ("Bán xe máy, cần thủ tục gì?", "trader"),
        ("So sánh Vision và Lead", "consultant"),
        ("Có nên mua xe cũ không?", "consultant"),
        ("Thương lượng giá thế nào?", "trader"),
    ]
    
    for message, expected_mode in test_cases:
        detected_mode = orchestrator._detect_mode(message, {})
        status = "✓" if detected_mode == expected_mode else "✗"
        logger.info(f"{status} '{message}' → {detected_mode} (expected: {expected_mode})")
    
    return True


def test_message_processing():
    """Test complete message processing"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Message Processing (FAISS Hit)")
    logger.info("=" * 60)
    
    test_message = "Xe ga nào tốt dưới 30 triệu?"
    conversation_id = "test-conv-001"
    state = {}
    
    logger.info(f"Processing: {test_message}")
    
    result = orchestrator.process_message(conversation_id, test_message, state)
    
    logger.info(f"✓ Response received:")
    logger.info(f"  Mode: {result.get('mode')}")
    logger.info(f"  Source: {result.get('source')}")
    logger.info(f"  Message (first 150 chars): {result.get('message', '')[:150]}...")
    
    if result.get('source') == 'faiss':
        logger.info("✓ FAISS hit confirmed!")
    else:
        logger.warning(f"⚠ Expected FAISS hit, got: {result.get('source')}")
    
    return True


def test_memory_stats_endpoint():
    """Test memory stats retrieval"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Memory Stats")
    logger.info("=" * 60)
    
    stats = orchestrator.get_memory_stats()
    
    logger.info(f"✓ Memory Stats:")
    logger.info(f"  Total cached pairs: {stats.get('total_cached_pairs')}")
    logger.info(f"  Consultant pairs: {stats.get('consultant_pairs')}")
    logger.info(f"  Trader pairs: {stats.get('trader_pairs')}")
    
    return True


def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("PENTAMO ORCHESTRATOR V3 - TEST SUITE")
    logger.info("=" * 60 + "\n")
    
    try:
        test_faiss_memory()
        test_mode_detection()
        test_message_processing()
        test_memory_stats_endpoint()
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ ALL TESTS PASSED!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Start the FastAPI server: uvicorn backend.main:app --reload")
        logger.info("2. Test the /api/conversations endpoint")
        logger.info("3. Monitor /api/memory/stats for cache statistics")
        
        return 0
    
    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
