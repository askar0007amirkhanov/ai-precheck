# Code Integrity & Safety Rules

## 1. Partial Edits
- **NEVER** use comments like `# ... imports ...` or `# ... rest of code ...` to replace existing code unless you are absolutely sure the tool supports it and you are not overwriting essential definitions.
- **ALWAYS** check for `NameError` or `ImportError` potential before applying `replace_file_content`.
- **Verify Context**: Ensure you are not removing the parent class, function definition, or variable initialization when editing a specific block.

## 2. Router & App Integrity
- When editing `router.py` or `main.py`, **ALWAYS** ensure `app = FastAPI(...)` and `router = APIRouter()` remain intact.
- **DO NOT** delete Pydantic models (`class RequestModel(BaseModel)`) even if you are just changing a function body.

## 3. Server Management
- **Check Processes**: Before starting a server, always check if one is already running to avoid port conflicts.
- **Restarting**: If the server needs a restart, ensure the previous process is terminated first.
