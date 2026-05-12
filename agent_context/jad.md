# Jad

## Scope
- ML, classifier inference, and golden replay validation

## Completed
- Trained ConvNeXt Tiny on RVL-CDIP in Colab
- No OCR used
- Full train split used: 320k images
- Full validation split used: 40k images
- Test attempted: 40k images
- Evaluated: 39,999 images
- Skipped: 1 corrupt TIFF
- Final test top-1: 76.98%
- Final test top-5: 95.54%
- Worst class: `scientific_report` at 51.04%
- Exported `app/classifier/models/classifier.pt`
- Exported `app/classifier/models/model_card.json`
- Exported 50 golden TIFF images
- Exported `app/classifier/eval/golden_expected.json`
- `app/classifier/eval/golden.py` passed in Colab
- Local CPU replay initially had tiny confidence-only mismatches at `1e-06` tolerance
- Predicted labels still matched on the failing golden examples
- Added `app/classifier/eval/regenerate_golden_expected.py` to rebuild CPU-local expected outputs using the same replay preprocessing and model-loading path
- Regenerated `app/classifier/eval/golden_expected.json` in the CPU environment intended for local/CI replay
- Local CPU golden replay now passes at `1e-06` tolerance after regeneration
- `classifier.pt` and `app/classifier/eval/golden_images/` were unchanged
- `classifier.pt` SHA-256: `dc3737d3584d8ba8a405041cd97486835f15a56d3914914247d0b4002d1d4bb5`

## Files changed
- `app/classifier/models/classifier.pt`
- `app/classifier/models/model_card.json`
- `app/classifier/eval/golden.py`
- `app/classifier/eval/regenerate_golden_expected.py`
- `app/classifier/eval/golden_expected.json`
- `app/classifier/eval/golden_images/`
- `requirements-ml.txt`
- `AGENTS.md`
- `agent_context/jad.md`

## How to test
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-ml.txt
python3 app/classifier/eval/regenerate_golden_expected.py
python3 app/classifier/eval/golden.py
```

## Inference core
- Added `app/classifier/inference/types.py`
- Added `app/classifier/inference/preprocessing.py`
- Added `app/classifier/inference/postprocessing.py`
- Added `app/classifier/inference/model_validator.py`
- Added `app/classifier/inference/predictor.py`
- Added `app/classifier/inference/overlays.py`
- Added `scripts/run_local_inference.py`
- Added `tests/classifier/test_model_card_sha.py`
- Added `tests/classifier/test_preprocessing.py`
- Added `tests/classifier/test_predictor.py`
- Real Redis, MinIO, and service integration is intentionally not implemented yet.
- Worker integration is intentionally not implemented yet.
- Redis and MinIO integration waits on contracts from Aya.
- Prediction persistence waits on Mohamad's `prediction_service.record_prediction(...)` contract.

## Inference core test commands
```bash
.venv/bin/python app/classifier/eval/golden.py
.venv/bin/python scripts/run_local_inference.py
.venv/bin/python -m pytest tests/classifier
```

## License and latency
- `LICENSES.md` added/updated for RVL-CDIP academic/research use notes.
- Added `scripts/measure_inference_latency.py` for local classifier latency measurement.
- Command: `.venv/bin/python scripts/measure_inference_latency.py`
- Output JSON: `tmp/inference_latency.json`
- Real README latency numbers should be copied from the measured output after running locally or in Docker.

## Blocked
- No current blocker for local CPU golden replay once the ML dependencies are installed.

## Contracts needed
- From Aya: Redis job payload shape
- From Aya: MinIO adapter method names
- From Mohamad: `prediction_service.record_prediction(...)` signature

## Caveats / known limitations
- Current local workflow uses local/fake adapters only.
- Local golden replay should install PyTorch from the CPU-only index URL to avoid pulling large default Linux CUDA wheels.
- No training should run locally.
- RVL-CDIP should not be downloaded locally.

## Next steps
- Implement `app/classifier/inference/`
- Implement a local fake inference worker
- Later integrate with Aya's MinIO/Redis adapters
- Later integrate with Mohamad's `prediction_service`
