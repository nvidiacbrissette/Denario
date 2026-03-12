import os
import re
import json
from pathlib import Path
import warnings
from urllib import request, error

from .llm import LLM, models

def input_check(str_input: str) -> str:
    """Check if the input is a string with the desired content or the path markdown file, in which case reads it to get the content."""

    if str_input.endswith(".md"):
        with open(str_input, 'r') as f:
            content = f.read()
    elif isinstance(str_input, str):
        content = str_input
    else:
        raise ValueError("Input must be a string or a path to a markdown file.")
    return content

def llm_parser(llm: LLM | str) -> LLM:
    """Get the LLM instance from a string."""

    if isinstance(llm, str):
        try:
            llm = models[llm]
        except KeyError:
            raise KeyError(f"LLM '{llm}' not available. Please select from: {list(models.keys())}")
    return llm

def extract_file_paths(markdown_text):
    """
    Extract the bulleted file paths from markdown text 
    and check if they exist and are absolute paths.
    
    Args:
        markdown_text (str): The markdown text containing file paths
    
    Returns:
        tuple: (existing_paths, missing_paths)
    """
    
    # Pattern to match file paths in markdown bullet points
    pattern = r'-\s*([^\n]+\.(?:csv|txt|md|py|json|yaml|yml|xml|html|css|js|ts|tsx|jsx|java|cpp|c|h|hpp|go|rs|php|rb|pl|sh|bat|sql|log))'
    
    # Find all matches
    matches = re.findall(pattern, markdown_text, re.IGNORECASE)
    
    # Clean up paths and check existence
    existing_paths = []
    missing_paths = []
    
    for match in matches:
        path = match.strip()
        if os.path.exists(path) and os.path.isabs(path):
            existing_paths.append(path)
        else:
            missing_paths.append(path)
    
    return existing_paths, missing_paths

def check_file_paths(content: str) -> None:
    """Check that file paths indicated in content text have the proper format"""

    existing_paths, missing_paths = extract_file_paths(content)

    if len(missing_paths) > 0:
        warnings.warn(
            f"The following data files paths in the data description are not in the right format or do not exist:\n"
            f"{missing_paths}\n"
            f"Please fix them according to the convention '- /absolute/path/to/file.ext'\n"
            f"otherwise this may cause hallucinations in the LLMs."
        )

    if len(existing_paths) == 0:
        warnings.warn(
            "No data files paths were found in the data description. If you want to provide input data, ensure that you indicate their path, otherwise this may cause hallucinations in the LLM in the get_results() workflow later on."
        )

NVIDIA_CLOUD_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_API_KEY_MODEL = "nvidia/nemotron-3-nano-30b-a3b"

def get_nvidia_base_url() -> str:
    """Return the NVIDIA endpoint URL.

    Set NIM_BASE_URL to point at a local NIM container (e.g. http://localhost:8000/v1).
    When unset, defaults to the NVIDIA cloud API.
    """
    return os.getenv("NIM_BASE_URL", NVIDIA_CLOUD_URL)

def get_nvidia_api_key() -> str:
    """Return the API key for the NVIDIA endpoint.

    For a local NIM container the key is typically unused (defaults to "EMPTY").
    For the NVIDIA cloud API, set NVIDIA_API_KEY in your environment.
    """
    return os.getenv("NVIDIA_API_KEY", "EMPTY")

def has_nvidia_api_key() -> bool:
    """Return True when a non-empty NVIDIA API key is provided."""
    api_key = get_nvidia_api_key().strip()
    return bool(api_key) and api_key.upper() != "EMPTY"

def get_nvidia_available_models() -> list[str]:
    """Fetch available model IDs from the configured NVIDIA endpoint."""
    base_url = get_nvidia_base_url().rstrip("/")
    api_key = get_nvidia_api_key()
    models_url = f"{base_url}/models"

    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = request.Request(models_url, headers=headers, method="GET")
        with request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            data = payload.get("data", [])
            return [m.get("id", "") for m in data if isinstance(m, dict) and m.get("id")]
    except (error.URLError, TimeoutError, json.JSONDecodeError):
        return []

def get_nvidia_available_models_strict() -> list[str]:
    """Fetch available model IDs and raise with endpoint context on failure."""
    base_url = get_nvidia_base_url().rstrip("/")
    api_key = get_nvidia_api_key()
    models_url = f"{base_url}/models"

    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = request.Request(models_url, headers=headers, method="GET")
        with request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            data = payload.get("data", [])
            models = [m.get("id", "") for m in data if isinstance(m, dict) and m.get("id")]
            if not models:
                raise ValueError(
                    "NVIDIA endpoint returned an empty model list. "
                    f"endpoint='{base_url}', requested_model='{NVIDIA_API_KEY_MODEL}'."
                )
            return models
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ValueError(
            "Failed to validate NVIDIA API-key model against endpoint. "
            f"endpoint='{base_url}', requested_model='{NVIDIA_API_KEY_MODEL}', "
            f"http_status={exc.code}, response='{body}'. "
            "Verify endpoint compatibility and API-key scope."
        ) from exc
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValueError(
            "Failed to validate NVIDIA API-key model against endpoint. "
            f"endpoint='{base_url}', requested_model='{NVIDIA_API_KEY_MODEL}', "
            f"error='{exc}'. Verify endpoint URL and network accessibility."
        ) from exc

def resolve_nvidia_model_name(configured_model: str) -> str:
    """Resolve the NVIDIA model name for local NIM and hosted endpoints."""
    override_model = os.getenv("NVIDIA_MODEL_NAME")
    if override_model:
        return override_model

    # API-key mode: force the exact requested model, no fallback.
    if has_nvidia_api_key():
        available_models = get_nvidia_available_models_strict()
        if NVIDIA_API_KEY_MODEL not in available_models:
            raise ValueError(
                "API-key mode requires a fixed NVIDIA model that is not available. "
                f"endpoint='{get_nvidia_base_url()}', requested_model='{NVIDIA_API_KEY_MODEL}', "
                f"available_models={available_models}. "
                "Verify endpoint compatibility and API-key scope."
            )
        return NVIDIA_API_KEY_MODEL

    available_models = get_nvidia_available_models()
    if not available_models:
        return configured_model

    if configured_model in available_models:
        return configured_model

    preferred = [m for m in available_models if "nemotron" in m.lower() and "nano" in m.lower()]
    if preferred:
        return preferred[0]

    raise ValueError(
        "Configured NVIDIA model is unavailable for this endpoint. "
        f"Configured='{configured_model}', available_models={available_models}. "
        "Set NVIDIA_MODEL_NAME to an exact model id."
    )

def nim_model_config(model_name: str) -> dict:
    """Build a cmbagent-compatible config dict for an NVIDIA NIM / cloud endpoint."""
    resolved_model = resolve_nvidia_model_name(model_name)
    return {
        "model": resolved_model,
        "api_key": get_nvidia_api_key(),
        "api_type": "openai",
        "base_url": get_nvidia_base_url(),
        "price": [0.0, 0.0],
    }

def maybe_nim_config(model_name: str) -> str | dict:
    """Return a NIM config dict if model_name is an NVIDIA model, otherwise pass through."""
    if isinstance(model_name, str) and 'nvidia' in model_name:
        return nim_model_config(model_name)
    return model_name

def create_work_dir(work_dir: str | Path, name: str) -> Path:
    """Create working directory"""

    work_dir = os.path.join(work_dir, f"{name}_generation_output")
    os.makedirs(work_dir, exist_ok=True)
    return Path(work_dir)

def get_task_result(chat_history, name: str):
    """Get task result from chat history"""
    
    for obj in chat_history[::-1]:
        if obj['name'] == name:
            result = obj['content']
            break
    task_result = result
    return task_result

def in_notebook():
    """Check whether the code is run from a Jupyter Notebook or not, to use different display options"""
    
    try:
        from IPython import get_ipython # type: ignore
        if 'IPKernelApp' not in get_ipython().config:  # type: ignore # pragma: no cover
            return False
    except ImportError:
        return False
    except AttributeError:
        return False
    return True
