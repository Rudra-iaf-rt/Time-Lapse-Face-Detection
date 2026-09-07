# Edge Deployment

CPU and CUDA-first edge pipeline. **TensorRT / Jetson are optional** — never required.

## Layout

```text
edge/
├── config/
├── pipeline/
├── inference/
├── optimizers/
├── devices/
├── monitoring/
└── api/
```

## Capability detection

```bash
python -m edge.devices.capability
```

Reports CPU / CUDA / ONNX / TensorRT availability and selects a safe backend.

## Data policy

Prefer metadata over raw video:

```json
{
  "camera_id": "CAM01",
  "global_id": "PERSON_0007",
  "timestamp": "2026-09-08T00:00:00Z",
  "event": "person_detected",
  "confidence": 0.91
}
```

Network failures: events buffer locally then flush when connectivity returns.
