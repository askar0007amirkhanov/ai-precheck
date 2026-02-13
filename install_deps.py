import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

if __name__ == "__main__":
    pkgs = [
        "pytest", 
        "pytest-asyncio", 
        "httpx", 
        "sqlalchemy", 
        "alembic",
        "pydantic",
        "pydantic-settings",
        "redis",
        "arq",
        "playwright",
        "beautifulsoup4",
        "jinja2",
        "tenacity",
        "openai",
        "google-generativeai",
        "weasyprint"
    ]
    for pkg in pkgs:
        try:
            print(f"Installing {pkg}...")
            install(pkg)
        except Exception as e:
            print(f"Failed to install {pkg}: {e}")

    print("Dependencies installed.")
