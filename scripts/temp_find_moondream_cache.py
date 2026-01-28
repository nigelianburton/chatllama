import os
from pathlib import Path

def _env_path(name: str) -> str:
    value = os.environ.get(name)
    return value if value else "(not set)"

print("Moondream cache locator")
print("========================")
print(f"HF_HOME={_env_path('HF_HOME')}")
print(f"HF_HUB_CACHE={_env_path('HF_HUB_CACHE')}")
print(f"TRANSFORMERS_CACHE={_env_path('TRANSFORMERS_CACHE')}")
print(f"TORCH_HOME={_env_path('TORCH_HOME')}")
print("")

cache_candidates = []

# Prefer HF cache locations.
try:
    from huggingface_hub.constants import HF_HUB_CACHE  # type: ignore
    cache_candidates.append(Path(HF_HUB_CACHE))
except Exception:
    pass

if os.environ.get("HF_HOME"):
    cache_candidates.append(Path(os.environ["HF_HOME"]) / "hub")
if os.environ.get("HF_HUB_CACHE"):
    cache_candidates.append(Path(os.environ["HF_HUB_CACHE"]))
if os.environ.get("TRANSFORMERS_CACHE"):
    cache_candidates.append(Path(os.environ["TRANSFORMERS_CACHE"]))

# Default Hugging Face cache locations.
home = Path.home()
cache_candidates.extend([
    home / ".cache" / "huggingface" / "hub",
    home / ".cache" / "huggingface" / "transformers",
])

# Torch cache as a fallback.
if os.environ.get("TORCH_HOME"):
    cache_candidates.append(Path(os.environ["TORCH_HOME"]))
else:
    cache_candidates.append(home / ".cache" / "torch")

# De-duplicate and keep existing directories only.
seen = set()
existing = []
for path in cache_candidates:
    try:
        resolved = path.expanduser().resolve()
    except Exception:
        resolved = path.expanduser()
    if resolved in seen:
        continue
    seen.add(resolved)
    if resolved.exists():
        existing.append(resolved)

if not existing:
    print("No cache directories found.")
    raise SystemExit(1)

print("Scanning cache roots:")
for root in existing:
    print(f"  - {root}")

print("")

needle = "moondream2"
matches = []
for root in existing:
    for path in root.rglob("*"):
        try:
            if needle in path.name.lower():
                matches.append(path)
        except Exception:
            continue

if not matches:
    print("No paths containing 'moondream2' found in cache roots.")
    raise SystemExit(2)

print("Matches:")
for match in sorted(matches):
    print(f"  - {match}")
