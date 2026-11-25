"""Multi-Persona Evaluator orchestrating data pipeline, OCR vision, and legal domain auditors."""

from typing import Any

from app.evaluation.data_pipeline_auditor import DataPipelineAuditor
from app.evaluation.legal_domain_auditor import LegalDomainAuditor
from app.evaluation.ocr_vision_auditor import OcrVisionAuditor


class MultiPersonaEvaluator:
    """Orchestrates 3 independent evaluation angles to compute an overall quality score."""

    def __init__(self):
        self.pipeline_auditor = DataPipelineAuditor()
        self.vision_auditor = OcrVisionAuditor()
        self.legal_auditor = LegalDomainAuditor()

    def evaluate_all(self) -> dict[str, Any]:
        """Run all three auditor personas and calculate weighted overall quality."""
        pipeline_res = self.pipeline_auditor.audit()
        vision_res = self.vision_auditor.audit()
        legal_res = self.legal_auditor.audit()

        # Weighted quality score: 35% pipeline, 35% vision, 30% legal
        overall_score = round(
            pipeline_res["score"] * 0.35 + vision_res["score"] * 0.35 + legal_res["score"] * 0.30,
            1,
        )

        all_passed = pipeline_res["passed"] and vision_res["passed"] and legal_res["passed"]

        return {
            "overall_quality_score": overall_score,
            "overall_passed": all_passed,
            "personas": {
                "data_pipeline": pipeline_res,
                "ocr_vision": vision_res,
                "legal_domain": legal_res,
            },
        }
