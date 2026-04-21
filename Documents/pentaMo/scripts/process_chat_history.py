import json
import os
import sys
import logging
from typing import Dict, Any, List

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from backend.orchestrator_v3 import AgentOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EvalPipeline")

class EvaluationPipeline:
    def __init__(self, history_path: str, ground_truth_path: str):
        self.history_path = history_path
        self.ground_truth_path = ground_truth_path
        self.orchestrator = AgentOrchestrator()
        
        with open(ground_truth_path, 'r') as f:
            self.ground_truth = json.load(f)

    def run(self):
        results = []
        with open(self.history_path, 'r') as f:
            for line in f:
                data = json.loads(line)
                conv_id = data["conversation_id"]
                messages = data["messages"]
                gt = self.ground_truth.get(conv_id, {})
                
                logger.info(f"Evaluating Conversation: {conv_id}")
                
                state = {
                    "participants": {"buyer_id": "eval_user"},
                    "lead_stage": "DISCOVERY",
                    "listing_context": {"id": "listing_123", "seller_id": "seller_456"}
                }
                
                actual_tools = []
                actual_slots = {}
                
                for msg in messages:
                    if msg["sender"] == "buyer":
                        resp = self.orchestrator.process_message(conv_id, msg["text"], state)
                        state = resp["state"]
                        if resp["source"] == "tool" or "search" in resp["source"]:
                            actual_tools.append(resp.get("tool_name", "search"))

                # Metrics calculation
                eval_data = self._calculate_metrics(conv_id, state, actual_tools, gt)
                results.append(eval_data)
        
        self._generate_report(results)

    def _calculate_metrics(self, conv_id: str, final_state: Dict[str, Any], tools: List[str], gt: Dict[str, Any]):
        # Lead Stage Accuracy
        stage_match = final_state.get("lead_stage") == gt.get("expected_lead_stage")
        
        # Slot Coverage (Brand, Model, Price)
        expected_slots = gt.get("expected_slots", {})
        actual_brands = final_state.get("brands", [])
        
        covered = 0
        total = len(expected_slots)
        if "brand" in expected_slots and any(b in actual_brands for b in [expected_slots["brand"]]):
            covered += 1
            
        slot_coverage = (covered / total * 100) if total > 0 else 100.0
        
        # Hallucination Check (Simplified: Check if AI claim matches DB)
        # For real scenarios, we would compare AI output against DB state
        hallucination_rate = 0.0 # Placeholder
        
        return {
            "conversation_id": conv_id,
            "stage_reached": final_state.get("lead_stage"),
            "expected_stage": gt.get("expected_lead_stage"),
            "stage_match": stage_match,
            "slot_coverage": slot_coverage,
            "tools_called": list(set(tools))
        }

    def _generate_report(self, results: List[Dict[str, Any]]):
        report_path = os.path.join(PROJECT_ROOT, "evaluation_report.md")
        with open(report_path, 'w') as f:
            f.write("# PentaMo AI Evaluation Report\n\n")
            f.write("## Overview Metrics\n")
            f.write(f"- Total Conversations: {len(results)}\n")
            
            f.write("\n## Detailed Results\n")
            f.write("| Conv ID | Stage (Actual/Exp) | Match | Slot Coverage | Tools |\n")
            f.write("|---------|-------------------|-------|---------------|-------|\n")
            for r in results:
                tools_str = ", ".join(r["tools_called"])
                f.write(f"| {r['conversation_id']} | {r['stage_reached']}/{r['expected_stage']} | {r['stage_match']} | {r['slot_coverage']:.1f}% | {tools_str} |\n")
        
        logger.info(f"Report generated at {report_path}")

if __name__ == "__main__":
    pipeline = EvaluationPipeline(
        history_path=os.path.join(PROJECT_ROOT, "data/chat_history.jsonl"),
        ground_truth_path=os.path.join(PROJECT_ROOT, "data/ground_truth.json")
    )
    pipeline.run()
