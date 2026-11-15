"""Optional local Prompt Guard 2 signal; never downloads or grants authority.

Provision the licensed model and runtime separately. A missing model, malformed
score, busy worker or timeout returns unavailable/injection=True. Cancelling an
await does not kill native inference: the single worker remains occupied until it
finishes, preventing an unbounded backlog of timed-out inference threads.
"""
import asyncio
from functools import lru_cache
import math
from pathlib import Path
import threading
from ..config import setting

MAX_CHARS = 18000
MAX_WINDOWS = 64
_FAILED = object()
_CACHE_LOCK = threading.Lock()


def _unavailable(reason):
    return {'injection': True, 'available': False, 'method': 'unavailable',
            'detector': 'prompt_guard_2', 'reason': reason}


def _load_local(path):
    # Imports remain optional. Only local safetensors are accepted; no pickle
    # weights, remote code, Hub resolution or implicit model installation.
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(path), local_files_only=True, trust_remote_code=False, use_safetensors=True).to('cpu').eval()
    labels = {int(key): str(value).upper() for key, value in model.config.id2label.items()}
    benign = [key for key, value in labels.items() if value in ('BENIGN', 'SAFE')]
    malicious = [key for key, value in labels.items() if value in ('MALICIOUS', 'INJECTION')]
    if set(labels) != {0, 1} or len(benign) != 1 or len(malicious) != 1:
        raise ValueError('Unsupported local model label mapping')
    malicious_index = malicious[0]

    def predict(text):
        # Evaluate every overlapping token window, rather than silently truncating
        # a late injection out of the classifier's 512-token context.
        encoded = tokenizer(text, truncation=True, max_length=512, stride=64,
            return_overflowing_tokens=True, padding=True, return_tensors='pt')
        encoded.pop('overflow_to_sample_mapping', None)
        if not 1 <= encoded['input_ids'].shape[0] <= MAX_WINDOWS:
            raise ValueError('Too many source windows')
        highest = 0.0
        with torch.inference_mode():
            for start in range(0, encoded['input_ids'].shape[0], 4):
                batch = {key: value[start:start + 4] for key, value in encoded.items()}
                logits = model(**batch).logits
                if logits.ndim != 2 or logits.shape[1] != 2 or not torch.isfinite(logits).all().item():
                    raise ValueError('Invalid classifier logits')
                highest = max(highest, float(torch.softmax(logits, dim=-1)[:, malicious_index].max().item()))
        return highest
    return predict


class LocalDetector:
    def __init__(self, path):
        self.path = path
        self._load_lock = threading.Lock()
        self._busy = threading.Lock()
        self._loaded = False
        self._predictor = None

    def initialize(self):
        with self._load_lock:
            if not self._loaded:
                try:
                    local = Path(self.path)
                    if not self.path or not local.is_dir():
                        raise ValueError('Local model directory required')
                    self._predictor = _load_local(local.resolve())
                except Exception:
                    self._predictor = None
                self._loaded = True
        return self._predictor is not None

    def run_claimed(self, text):
        try:
            if not self.initialize():
                return None
            return self._predictor(text)
        except Exception:
            # A timed-out caller may no longer be awaiting this future. Keep raw
            # exceptions (including source text/model paths) out of executor logs.
            return _FAILED
        finally:
            self._busy.release()


@lru_cache(maxsize=4)
def _cached_detector(path):
    return LocalDetector(path)


def detector_for(path):
    # functools.lru_cache alone permits duplicate concurrent first executions.
    with _CACHE_LOCK:
        return _cached_detector(path)


detector_for.cache_clear = _cached_detector.cache_clear


def initialize(model_path=None):
    """Single-load synchronous startup hook. Call off the event loop."""
    path = str(model_path) if model_path is not None else setting('PROMPT_GUARD_MODEL_PATH')
    available = detector_for(path).initialize()
    return {'available': True, 'method': 'prompt_guard_2'} if available else _unavailable('model_unavailable')


async def classify(text, *, model_path=None, threshold=0.5, timeout_seconds=None):
    """Return a bounded signal; caller must retain deterministic authorization."""
    try:
        timeout = float(setting('PROMPT_GUARD_TIMEOUT_SECONDS', '5')) if timeout_seconds is None else timeout_seconds
        if (not isinstance(text, str) or not text.strip() or len(text) > MAX_CHARS
                or type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 < threshold < 1
                or type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 120):
            return _unavailable('invalid_input_or_configuration')
    except (TypeError, ValueError):
        return _unavailable('invalid_input_or_configuration')
    path = str(model_path) if model_path is not None else setting('PROMPT_GUARD_MODEL_PATH')
    detector = detector_for(path)
    if not detector._busy.acquire(blocking=False):
        return _unavailable('busy')
    try:
        future = asyncio.get_running_loop().run_in_executor(None, detector.run_claimed, text)
        value = await asyncio.wait_for(asyncio.shield(future), timeout=timeout)
    except asyncio.CancelledError:
        raise
    except TimeoutError:
        return _unavailable('timeout')
    except Exception:
        return _unavailable('inference_failed')
    if value is None:
        return _unavailable('model_unavailable')
    if value is _FAILED:
        return _unavailable('inference_failed')
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        return _unavailable('invalid_score')
    return {'injection': value >= threshold, 'available': True,
            'method': 'prompt_guard_2', 'score': value}
