"""Before unpickling deployed artifacts, validate the exact bytes that will be loaded."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

import joblib


ROOT = Path(__file__).resolve().parents[1] / "models"
MANIFEST = ROOT / "trusted_artifacts.json"
MAX_ARTIFACT = 2_000_000


def load_packaged_artifact(path: Path):
    path = Path(path)
    with path.open("rb") as stream:
        content = stream.read(MAX_ARTIFACT + 1)
    if len(content) > MAX_ARTIFACT:
        raise ValueError("Model artifact exceeds size limit")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if sha256(content).hexdigest() != manifest.get(path.name):
        raise ValueError("Packaged model integrity check failed")
    return joblib.load(BytesIO(content))
