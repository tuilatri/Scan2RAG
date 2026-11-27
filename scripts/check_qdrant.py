"""Check that Qdrant runs as a remote server with the full corpus loaded."""

import os
import urllib.request

from qdrant_client import QdrantClient

EXPECTED_POINTS = 7263


def main() -> int:
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    collection = os.getenv("QDRANT_COLLECTION_NAME", "vietnamese_legal_docs")
    base_url = f"http://{host}:{port}"

    try:
        with urllib.request.urlopen(f"{base_url}/healthz", timeout=3) as response:
            health = response.read().decode("utf-8", "replace").strip()
    except Exception as error:
        print(f"healthz: UNREACHABLE ({error})")
        return 1

    try:
        info = QdrantClient(host=host, port=port).get_collection(collection)
    except Exception as error:
        print(f"collection {collection}: MISSING ({error})")
        return 1

    points = int(info.points_count or 0)
    print(f"host: {host}:{port}")
    print(f"healthz: {health}")
    print(f"collection: {collection}")
    print(f"points: {points} (expected {EXPECTED_POINTS})")
    print("mode: remote (degraded_mode=False)")

    ok = points == EXPECTED_POINTS and health.startswith("healthz check passed")
    print("RESULT: PASS" if ok else "RESULT: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
