import os
from pathlib import Path

dirs = [
    "app/core",
    "app/infrastructure",
    "app/services/llm",
    "app/services/crawler",
    "app/services/pdf",
    "app/modules/compliance",
    "app/modules/policies",
    "app/modules/onboarding",
    "app/modules/auditing",
    "app/api/widget",
    "app/worker"
]

base_dir = Path("c:/AI_precheck")

for d in dirs:
    path = base_dir / d
    path.mkdir(parents=True, exist_ok=True)
    # Create __init__.py in each directory to make them packages
    (path / "__init__.py").touch()

print("Directories created successfully.")
