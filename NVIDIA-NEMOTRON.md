# NVIDIA Nemotron Integration

## Why These Changes Were Made

This diff addresses two practical issues when running Denario with Nemotron:

1. NVIDIA model IDs are not always identical across deployment targets (hosted endpoint vs on-prem NIM).
2. The LangGraph fast path had a node/state-name collision (`referee`) that blocked execution before model calls.

The result is a setup that supports both:
- NVIDIA hosted API endpoints
- Local/on-prem NIM endpoints


## What Changed (By File)

### `denario/utils.py`

- Added NVIDIA endpoint helpers:
  - `get_nvidia_base_url()`
  - `get_nvidia_api_key()`
- Added adaptive model-resolution helpers:
  - `get_nvidia_available_models()`
  - `resolve_nvidia_model_name(...)`
- Added API-key mode enforcement:
  - If `NVIDIA_API_KEY` is present, force model:
    - `nvcr.io/nim/nvidia/nemotron-3-nano:latest`
  - No fallback in API-key mode.
  - Fail fast with endpoint/model context when invalid.
- Updated `nim_model_config(...)` so cmbagent paths use the same resolved model logic.

### `denario/langgraph_agents/reader.py`

- NVIDIA branch now uses resolved model names (not hardcoded model IDs).
- Keeps base URL and API key sourcing through shared utils helpers.

### `denario/paper_agents/reader.py`

- Same NVIDIA resolver wiring as LangGraph reader.

### `denario/experiment.py`, `denario/idea.py`, `denario/method.py`

- cmbagent orchestration calls now pass model settings through `maybe_nim_config(...)`.
- This ensures non-LangGraph stages also inherit the same endpoint/model resolution behavior.

### `denario/key_manager.py`

- Added `NVIDIA_API_KEY` loading so key-based hosted mode can be configured consistently.

### `denario/langgraph_agents/agents_graph.py`

- Fixed node collision:
  - `referee` node renamed to `referee_node`.

### `denario/langgraph_agents/routers.py`

- Updated router target to `referee_node` for `task == 'referee'`.

### `denario/llm.py`

- Added alias:
  - `nemotron-nano` -> NVIDIA Nemotron model entry.


## Runtime Modes

### Hosted NVIDIA Endpoint Mode

Trigger:
- `NVIDIA_API_KEY` is set (non-empty, not `EMPTY`)

Behavior:
- Model is forced to:
  - `nvcr.io/nim/nvidia/nemotron-3-nano:latest`
- No fallback to discovery.
- If endpoint does not expose that model, fail immediately with a clear error.

### On-Prem NIM Mode

Trigger:
- `NIM_BASE_URL` points to local NIM (for example `http://localhost:8000/v1`)
- API-key enforcement is not active

Behavior:
- Model resolution order:
  1. `NVIDIA_MODEL_NAME` (explicit override)
  2. Exact configured model if available on `/models`
  3. First discovered model containing both `nemotron` and `nano`
  4. Error with available-model list if nothing matches


## Environment Variables

- `NIM_BASE_URL`
  - Endpoint URL.
  - Default: `https://integrate.api.nvidia.com/v1`
- `NVIDIA_API_KEY`
  - Enables hosted API-key mode and forced model string behavior.
- `NVIDIA_MODEL_NAME`
  - Optional explicit model ID override (highest precedence outside forced API-key path).


## Quick Start Commands

### Hosted Endpoint

```bash
export NVIDIA_API_KEY="<your-key>"
cd /home/cbrissette/Denario/examples
python3 nemotron-workflow.py
```

### On-Prem NIM

```bash
export NIM_BASE_URL="http://localhost:8000/v1"
export NVIDIA_API_KEY="EMPTY"
# Optional explicit pin:
# export NVIDIA_MODEL_NAME="<model-id-from-/models>"
cd /home/cbrissette/Denario/examples
python3 nemotron-workflow.py
```


## Troubleshooting

- `Model ... is unknown, check available_models`
  - Endpoint/model mismatch.
  - For on-prem NIM, inspect `/models` and optionally set `NVIDIA_MODEL_NAME`.
- `API-key mode requires a fixed NVIDIA model that is not available`
  - Hosted endpoint does not expose `nvcr.io/nim/nvidia/nemotron-3-nano:latest` for your key/endpoint.
- `401 Unauthorized`
  - Invalid or expired `NVIDIA_API_KEY`, or key lacks access to requested model.
- Data path warnings in `input.md`
  - Example warns when paths are not absolute; this affects result quality, not model wiring.
- Python 3.10 FutureWarnings
  - Non-fatal; upgrade recommended for longer-term compatibility.
