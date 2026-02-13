import asyncio
import sys
import os

# Ensure app is in path
sys.path.append(os.getcwd())

from app.api.compliance.router import run_compliance_check, ComplianceRequest
from app.services.report.docx_service import DocxService # Verify import exists
from fastapi import HTTPException

async def main():
    print("Running debug compliance check...")
    
    req = ComplianceRequest(
        url="https://google.com",
        company_name="Debug Corp"
    )
    
    try:
        response = await run_compliance_check(req)
        print("Success! Response media type:", response.media_type)
        print("Response body length:", len(response.body))
    except HTTPException as e:
        print(f"Caught HTTPException: {e.detail}")
    except Exception as e:
        print(f"Caught UNEXPECTED Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
