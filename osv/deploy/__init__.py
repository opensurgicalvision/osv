"""Export pipelines, ONNX Runtime, TensorRT INT8 quantization, and latency benchmarks."""

from typing import Any


def get_latency_budget() -> dict[str, Any]:
    """Returns official real-time inference latency budget (<= 50ms, >= 30 FPS)."""
    return {
        "target_latency_p95_ms": 50.0,
        "target_fps": 30.0,
        "supported_engines": ["PyTorch", "ONNXRuntime", "TensorRT"],
    }


__all__ = ["get_latency_budget"]
