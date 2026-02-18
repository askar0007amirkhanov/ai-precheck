"""
Widget API — serves JS widget and policy content for merchant sites.
Public endpoints (no API key needed), but domain-locked via widget token.
"""
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends
from pydantic import BaseModel
import uuid

from app.infrastructure.database import get_db
from app.modules.policies.models import Widget, ClientPolicy
from app.modules.policies.generator import POLICY_TYPES

logger = logging.getLogger(__name__)

router = APIRouter()


WIDGET_JS_TEMPLATE = """
(function() {
    'use strict';
    var TOKEN = '%TOKEN%';
    var API_BASE = '%API_BASE%';

    // Fetch approved policies
    fetch(API_BASE + '/api/widget/' + TOKEN + '/policies')
        .then(function(r) { return r.json(); })
        .then(function(policies) {
            if (!policies.length) return;
            injectPolicies(policies);
        })
        .catch(function(e) { console.warn('Policy widget error:', e); });

    function injectPolicies(policies) {
        // Create footer container
        var container = document.createElement('div');
        container.id = 'compliance-policies';
        container.style.cssText = 'text-align:center;padding:16px;border-top:1px solid #e0e0e0;margin-top:24px;font-family:sans-serif;font-size:13px;';

        var label = document.createElement('span');
        label.textContent = 'Policies: ';
        label.style.color = '#666';
        container.appendChild(label);

        policies.forEach(function(p, i) {
            if (i > 0) {
                var sep = document.createElement('span');
                sep.textContent = ' | ';
                sep.style.color = '#ccc';
                container.appendChild(sep);
            }
            var link = document.createElement('a');
            link.href = '#';
            link.textContent = p.name;
            link.style.cssText = 'color:#0066cc;text-decoration:none;';
            link.onclick = function(e) {
                e.preventDefault();
                showModal(p.name, p.html);
            };
            container.appendChild(link);
        });

        // Append to body
        if (document.body) {
            document.body.appendChild(container);
        } else {
            document.addEventListener('DOMContentLoaded', function() {
                document.body.appendChild(container);
            });
        }
    }

    function showModal(title, html) {
        // Remove existing modal
        var existing = document.getElementById('policy-modal-overlay');
        if (existing) existing.remove();

        var overlay = document.createElement('div');
        overlay.id = 'policy-modal-overlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%%;height:100%%;background:rgba(0,0,0,0.6);z-index:99999;display:flex;align-items:center;justify-content:center;';

        var modal = document.createElement('div');
        modal.style.cssText = 'background:#fff;border-radius:8px;max-width:700px;width:90%%;max-height:80vh;overflow-y:auto;padding:32px;position:relative;box-shadow:0 8px 32px rgba(0,0,0,0.3);';

        var closeBtn = document.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = 'position:absolute;top:12px;right:16px;background:none;border:none;font-size:20px;cursor:pointer;color:#666;';
        closeBtn.onclick = function() { overlay.remove(); };

        var titleEl = document.createElement('h2');
        titleEl.textContent = title;
        titleEl.style.cssText = 'margin:0 0 16px;font-size:22px;color:#333;';

        var content = document.createElement('div');
        content.innerHTML = html;
        content.style.cssText = 'line-height:1.6;color:#444;';

        modal.appendChild(closeBtn);
        modal.appendChild(titleEl);
        modal.appendChild(content);
        overlay.appendChild(modal);

        overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };
        document.body.appendChild(overlay);
    }
})();
"""



class WidgetCreateRequest(BaseModel):
    client_id: str
    domain: str


@router.post("/create", summary="Create or retrieve widget token")
async def create_widget(
    request: WidgetCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate or retrieve a widget token for a client domain."""
    # Check if exists
    stmt = select(Widget).where(Widget.client_id == request.client_id)
    result = await db.execute(stmt)
    widget = result.scalar_one_or_none()

    if not widget:
        token = str(uuid.uuid4())
        widget = Widget(
            client_id=request.client_id,
            domain=request.domain,
            token=token,
            is_active=True
        )
        db.add(widget)
        await db.commit()
        await db.refresh(widget)
    
    return {"token": widget.token, "client_id": widget.client_id}


@router.get("/{token}/policies.js", summary="Widget JS script")
async def get_widget_script(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Serve the widget JavaScript. Merchant embeds this on their site."""
    # Validate token
    stmt = select(Widget).where(Widget.token == token, Widget.is_active == True)
    result = await db.execute(stmt)
    widget = result.scalar_one_or_none()
    if not widget:
        return Response(
            content="/* Widget not found or inactive */",
            media_type="application/javascript",
        )

    # Build API base URL
    api_base = str(request.base_url).rstrip("/")

    js = WIDGET_JS_TEMPLATE.replace("%TOKEN%", token).replace("%API_BASE%", api_base)

    return Response(content=js, media_type="application/javascript")


@router.get("/{token}/policies", summary="List approved policies for widget")
async def get_widget_policies(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Return approved policies for a widget token (used by the JS widget)."""
    # Validate widget
    stmt = select(Widget).where(Widget.token == token, Widget.is_active == True)
    result = await db.execute(stmt)
    widget = result.scalar_one_or_none()
    if not widget:
        return []

    # Fetch approved policies for this client
    stmt = select(ClientPolicy).where(
        ClientPolicy.client_id == widget.client_id,
        ClientPolicy.status == "approved",
    )
    result = await db.execute(stmt)
    policies = result.scalars().all()

    return [
        {
            "type": p.policy_type,
            "name": POLICY_TYPES.get(p.policy_type, p.policy_type),
            "html": p.content_html,
        }
        for p in policies
    ]


@router.get("/{token}/policy/{policy_type}", response_class=HTMLResponse, summary="Single policy HTML")
async def get_single_policy(
    token: str,
    policy_type: str,
    db: AsyncSession = Depends(get_db),
):
    """Return a single approved policy as HTML page."""
    # Validate widget
    stmt = select(Widget).where(Widget.token == token, Widget.is_active == True)
    result = await db.execute(stmt)
    widget = result.scalar_one_or_none()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found.")

    # Fetch policy
    stmt = select(ClientPolicy).where(
        ClientPolicy.client_id == widget.client_id,
        ClientPolicy.policy_type == policy_type,
        ClientPolicy.status == "approved",
    )
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found or not approved.")

    policy_name = POLICY_TYPES.get(policy_type, policy_type)

    html = f"""<!DOCTYPE html>
<html lang="{policy.language}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{policy_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               max-width: 750px; margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.7; }}
        h2 {{ color: #222; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
        h3 {{ color: #444; }}
        a {{ color: #0066cc; }}
    </style>
</head>
<body>
    {policy.content_html}
</body>
</html>"""

    return HTMLResponse(content=html)
