"""Audit original and final Phase 3.5 examples against all older data."""
import json

from .ml_v3_data import DEVELOPMENT as V3_DEV, FINAL as V3_FINAL, read
from .phase25_audit import Source, _legacy, check
from .phase25_data import DEVELOPMENT as V2_DEV, FINAL as V2_FINAL
from .phase35_data import DEVELOPMENT, FINAL


def audit():
    history = list(_legacy())
    for path in (V2_DEV, V2_FINAL, V3_DEV, V3_FINAL):
        for row in read(path):
            history.extend(Source(text, row["id"], "historical")
                           for text in [row["source"], *row["accepted"], *row.get("rejected", [])])
    return check(read(DEVELOPMENT), read(FINAL) if FINAL.is_file() else [], historical=history)


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["issues"] or result["cross_split_near_pairs"]))
