"""Unified Enterprise Profile API — one record per customer."""

import os, uuid, json, shutil
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/enterprise-profile", tags=["Enterprise Profile"])
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads", "enterprise")

@router.get("")
async def get_profile(
    customer_id: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Admin can query any customer; regular users see only their own
    cid = str(customer_id) if (current_user.get("is_super_admin") and customer_id) else str(current_user["customer_id"])
    result = await db.execute(
        text("SELECT data_json FROM enterprise_profiles WHERE customer_id = :cid"),
        {"cid": cid},
    )
    row = result.fetchone()
    if row and row[0]:
        return {"customer_id": cid, "data": json.loads(row[0])}
    return {"customer_id": cid, "data": {}}


@router.put("")
async def save_profile(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Admin can save any customer; regular users save only their own
    req_cid = body.get("customer_id")
    cid = str(req_cid) if (current_user.get("is_super_admin") and req_cid) else str(current_user["customer_id"])
    data_json = json.dumps(body.get("data", {}), ensure_ascii=False)
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        text("""
            INSERT INTO enterprise_profiles (id, customer_id, data_json, updated_at)
            VALUES (:id, :cid, :data, :now)
            ON CONFLICT(customer_id) DO UPDATE SET data_json = :data2, updated_at = :now2
        """),
        {"id": str(uuid.uuid4()), "cid": cid, "data": data_json, "data2": data_json, "now": now, "now2": now},
    )
    await db.commit()
    return {"saved": True}


@router.post("/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    category: str = Form("photos"),
    customer_id: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upload files for the enterprise profile. Returns file paths."""
    cid = str(customer_id) if (current_user.get("is_super_admin") and customer_id) else str(current_user["customer_id"])
    folder = os.path.join(UPLOAD_DIR, cid, category)
    os.makedirs(folder, exist_ok=True)

    saved = []
    for f in files:
        safe_name = f.filename.replace("\\", "/").split("/")[-1] if f.filename else "file"
        filepath = os.path.join(folder, safe_name)
        with open(filepath, "wb") as buf:
            shutil.copyfileobj(f.file, buf)
        saved.append(f"/uploads/enterprise/{cid}/{category}/{safe_name}")

    # Update profile with file paths
    result = await db.execute(
        text("SELECT data_json FROM enterprise_profiles WHERE customer_id = :cid"),
        {"cid": cid},
    )
    row = result.fetchone()
    data = json.loads(row[0]) if row and row[0] else {}
    existing = data.get(category, "")
    if isinstance(existing, list): existing = ", ".join(existing)
    new_paths = ", ".join(saved)
    data[category] = (existing + "\n" + new_paths).strip() if existing else new_paths

    data_json = json.dumps(data, ensure_ascii=False)
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        text("""
            INSERT INTO enterprise_profiles (id, customer_id, data_json, updated_at)
            VALUES (:id, :cid, :data, :now)
            ON CONFLICT(customer_id) DO UPDATE SET data_json = :data2, updated_at = :now2
        """),
        {"id": str(uuid.uuid4()), "cid": cid, "data": data_json, "data2": data_json, "now": now, "now2": now},
    )
    await db.commit()
    return {"uploaded": len(saved), "paths": saved, "category": category}
