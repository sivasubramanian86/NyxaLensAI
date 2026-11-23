"""Structured per-subagent traces for CloudWatch EMF and X-Ray."""
from __future__ import annotations

import json
import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)

# US on-demand estimates per 1K tokens. Refresh when model IDs or region change.
_RATES = {
    "amazon.nova-lite-v1:0": (0.00006, 0.00024),
    "anthropic.claude-3-5-sonnet-20241022-v2:0": (0.006, 0.03),
    "amazon.titan-embed-text-v2:0": (0.00002, 0.0),
}


def _text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)


def _tokens(value: Any) -> int:
    return math.ceil(len(_text(value)) / 4)


class PipelineSpan:
    def __init__(self, subagent: str, model_id: str, input_value: Any) -> None:
        self.subagent = subagent
        self.model_id = model_id
        self.input_value = input_value
        self.started = time.perf_counter()
        self._xray = None
        try:
            from aws_xray_sdk.core import xray_recorder
            self._xray = xray_recorder.begin_subsegment(subagent)
        except Exception:
            pass

    def finish(self, output_value: Any, citations_verified: int = 0, citations_stripped: int = 0) -> dict:
        duration = max(0, int((time.perf_counter() - self.started) * 1000))
        input_tokens = _tokens(self.input_value)
        output_tokens = _tokens(output_value)
        rates = [_RATES.get(model.strip(), (0.0, 0.0)) for model in self.model_id.split("+")]
        cost = (input_tokens * sum(rate[0] for rate in rates) + output_tokens * sum(rate[1] for rate in rates)) / 1000
        entry = {
            "subagent": self.subagent,
            "duration_ms": duration,
            "model_id": self.model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_usd": round(cost, 8),
            "citations_verified": citations_verified,
            "citations_stripped": citations_stripped,
        }
        emf = {
            "_aws": {"Timestamp": int(time.time() * 1000), "CloudWatchMetrics": [{
                "Namespace": "NyxaLensAI/Pipeline",
                "Dimensions": [["subagent", "model_id"]],
                "Metrics": [{"Name": "duration_ms", "Unit": "Milliseconds"},
                            {"Name": "input_tokens", "Unit": "Count"},
                            {"Name": "output_tokens", "Unit": "Count"},
                            {"Name": "estimated_usd", "Unit": "None"},
                            {"Name": "citations_verified", "Unit": "Count"},
                            {"Name": "citations_stripped", "Unit": "Count"}],
            }]},
            **entry,
        }
        logger.info(json.dumps(emf, separators=(",", ":")))
        if self._xray:
            try:
                self._xray.put_metadata("pipeline_trace", entry)
                from aws_xray_sdk.core import xray_recorder
                xray_recorder.end_subsegment()
            except Exception:
                pass
        return entry


def start_span(subagent: str, model_id: str, input_value: Any) -> PipelineSpan:
    return PipelineSpan(subagent, model_id, input_value)
