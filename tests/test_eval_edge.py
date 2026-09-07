# tests/test_eval_edge.py
from eval.metrics import GROUND_TRUTH_NOT_AVAILABLE
from eval.reid_evaluator import ReidEvaluator
from eval.tracking_metrics import evaluate_tracking
from eval.fusion_metrics import run_ablation
from edge.devices.capability import detect_capabilities
from edge.pipeline.metadata_emitter import MetadataEmitter


def test_reid_without_gt():
    result = ReidEvaluator().evaluate([], [], None)
    assert result["status"] == GROUND_TRUTH_NOT_AVAILABLE


def test_tracking_without_gt():
    result = evaluate_tracking([], None)
    assert result["status"] == GROUND_TRUTH_NOT_AVAILABLE


def test_fusion_empty():
    result = run_ablation([])
    assert result["status"] == GROUND_TRUTH_NOT_AVAILABLE


def test_edge_capability():
    caps = detect_capabilities()
    assert caps.cpu is True
    assert caps.preferred_backend in {"cpu", "cuda", "onnx", "tensorrt"}


def test_metadata_emitter_buffers_on_failure(tmp_path):
    def fail_send(_payload):
        return False

    emitter = MetadataEmitter(
        send_fn=fail_send,
        buffer_path=str(tmp_path / "buf.jsonl"),
    )
    ok = emitter.emit("CAM01", "PERSON_0007", "person_detected", 0.91)
    assert ok is False
    assert len(emitter.buffer) == 1
