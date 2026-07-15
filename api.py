"""
OMR Test Manager — REST API
Run with: python api.py
Docs:      http://localhost:8000/docs
"""

import os
import sys
import csv
import json
import secrets
import shutil
import tempfile
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import (
    FastAPI, HTTPException, Depends, UploadFile, File,
    Security, BackgroundTasks, status
)
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

# ─── Shared application modules ────────────────────────────────────────────────
from index import (
    Database, SettingsManager, PDFProcessor, FirestoreUploader,
    CONFIG_FILE, DB_FILE
)

# ─── API Configuration ──────────────────────────────────────────────────────────
API_VERSION = "v1"
API_PREFIX  = f"/api/{API_VERSION}"


def _get_or_create_api_key() -> str:
    """Load the API key from config, or generate and persist a new one."""
    settings = SettingsManager()
    key = settings.data.get("api_key")
    if not key:
        key = secrets.token_urlsafe(32)
        settings.data["api_key"] = key
        settings.save()
    return key


API_KEY = _get_or_create_api_key()

# ─── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="OMR Test Manager API",
    description=(
        "REST API for the OMR Test Manager desktop application.\n\n"
        "### Authentication\n"
        "Every request must include the `X-API-Key` header.\n"
        "The key is printed to the console when the server starts, "
        "and stored in `app_config.json`.\n\n"
        "### Quick Start\n"
        "1. Create a test → `POST /api/v1/tests`\n"
        "2. Upload a scanned PDF → `POST /api/v1/tests/{id}/upload-pdf`\n"
        "3. Run OMR grading → `POST /api/v1/tests/{id}/run`\n"
        "4. Fetch results → `GET /api/v1/tests/{id}/results`\n"
        "5. Push to Firestore → `POST /api/v1/tests/{id}/push-firestore`\n"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Auth ───────────────────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: Optional[str] = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass it as the 'X-API-Key' header.",
        )
    return key


# ─── Thread-local DB factory ─────────────────────────────────────────────────
import threading as _threading
_local = _threading.local()
_settings = SettingsManager(CONFIG_FILE)

def get_db() -> Database:
    """Return a per-thread SQLite connection so FastAPI's threadpool is safe."""
    if not hasattr(_local, "db"):
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(DB_FILE, check_same_thread=False)
        db = Database.__new__(Database)
        db.conn   = conn
        db.cursor = conn.cursor()
        db._create_table()
        _local.db = db
    return _local.db

def get_settings() -> SettingsManager: return _settings

def get_processor(test_id: int) -> PDFProcessor:
    s = get_settings()
    s.current_test_id = test_id
    return PDFProcessor(s)


# ═══════════════════════════════════════════════════════════════════════════════
#  Pydantic Models
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreate(BaseModel):
    name: str            = Field(..., min_length=1, json_schema_extra={"example": "Semester 1 Midterm"})
    date: str            = Field(..., description="YYYY-MM-DD format", json_schema_extra={"example": "2026-07-13"})
    template_folder: str = Field(..., json_schema_extra={"example": "sample1"})

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be in YYYY-MM-DD format")
        return v


class TestUpdate(BaseModel):
    name:            Optional[str] = Field(None, json_schema_extra={"example": "Semester 1 Final"})
    date:            Optional[str] = Field(None, json_schema_extra={"example": "2026-08-01"})
    template_folder: Optional[str] = Field(None, json_schema_extra={"example": "sample2"})

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("date must be in YYYY-MM-DD format")
        return v


class TestOut(BaseModel):
    id:              int
    name:            str
    date:            str
    template_folder: str


class RunStatus(BaseModel):
    test_id: int
    status:  str
    message: str


class SettingsOut(BaseModel):
    input_dir:            str
    output_dir:           str
    templates_dir:        str
    firestore_collection: str
    firestore_auth_key:   str


# ─── In-memory job tracker (keyed by test_id) ──────────────────────────────────
_jobs: dict[int, dict] = {}     # test_id → {"status": "running"|"done"|"error", "message": str}


# ═══════════════════════════════════════════════════════════════════════════════
#  Health & System
# ═══════════════════════════════════════════════════════════════════════════════

@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    response_description="API is healthy",
)
def health():
    """Returns a simple health status. No authentication required."""
    return {"status": "healthy", "api_version": API_VERSION}


@app.get(
    f"{API_PREFIX}/settings",
    tags=["System"],
    summary="Get current application settings",
    response_model=SettingsOut,
    dependencies=[Depends(require_api_key)],
)
def get_settings_endpoint():
    """Returns the active paths and Firestore configuration."""
    s = get_settings()
    return SettingsOut(
        input_dir            = s.get("input_dir", base_only=True) or "",
        output_dir           = s.get("output_dir", base_only=True) or "",
        templates_dir        = s.get("templates_dir") or "",
        firestore_collection = s.get("firestore_collection", "test_results"),
        firestore_auth_key   = s.get("firestore_auth_key") or "",
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Templates
# ═══════════════════════════════════════════════════════════════════════════════

@app.get(
    f"{API_PREFIX}/templates",
    tags=["Templates"],
    summary="List available OMR templates",
    dependencies=[Depends(require_api_key)],
)
def list_templates():
    """
    Scans the configured templates directory and returns all folders
    that contain a valid `template.json` file.
    """
    templates_dir = get_settings().get("templates_dir")
    if not templates_dir or not os.path.exists(templates_dir):
        return {"templates": [], "templates_dir": templates_dir}

    found = []
    for root, dirs, files in os.walk(templates_dir):
        if "template.json" in files:
            rel = os.path.relpath(root, templates_dir)
            if rel != ".":
                found.append(rel.replace("\\", "/"))
    found.sort()
    return {"templates": found, "templates_dir": templates_dir}


# ═══════════════════════════════════════════════════════════════════════════════
#  Tests CRUD
# ═══════════════════════════════════════════════════════════════════════════════

@app.get(
    f"{API_PREFIX}/tests",
    tags=["Tests"],
    summary="List all tests",
    response_model=List[TestOut],
    dependencies=[Depends(require_api_key)],
)
def list_tests():
    """Returns all tests stored in the local database, newest first."""
    rows = get_db().get_all_tests()
    return [TestOut(id=r[0], name=r[1], date=r[2], template_folder=r[3]) for r in rows]


@app.post(
    f"{API_PREFIX}/tests",
    tags=["Tests"],
    summary="Create a new test",
    response_model=TestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_test(body: TestCreate):
    """Creates a new test record with the given name, date, and OMR template."""
    _check_template_exists(body.template_folder)
    test_id = get_db().insert_test(body.name, body.date, body.template_folder)
    return TestOut(id=test_id, name=body.name, date=body.date, template_folder=body.template_folder)


@app.get(
    f"{API_PREFIX}/tests/{{test_id}}",
    tags=["Tests"],
    summary="Get a specific test",
    response_model=TestOut,
    dependencies=[Depends(require_api_key)],
)
def get_test(test_id: int):
    """Retrieves a single test by its ID."""
    row = get_db().get_test(test_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Test {test_id} not found.")
    return TestOut(id=row[0], name=row[1], date=row[2], template_folder=row[3])


@app.patch(
    f"{API_PREFIX}/tests/{{test_id}}",
    tags=["Tests"],
    summary="Update a test",
    response_model=TestOut,
    dependencies=[Depends(require_api_key)],
)
def update_test(test_id: int, body: TestUpdate):
    """Partially updates a test's name, date, or template."""
    row = get_db().get_test(test_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Test {test_id} not found.")
    name   = body.name            or row[1]
    date   = body.date            or row[2]
    tmpl   = body.template_folder or row[3]
    if body.template_folder:
        _check_template_exists(body.template_folder)
    get_db().update_test(test_id, name, date, tmpl)
    return TestOut(id=test_id, name=name, date=date, template_folder=tmpl)


@app.delete(
    f"{API_PREFIX}/tests/{{test_id}}",
    tags=["Tests"],
    summary="Delete a test",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)],
)
def delete_test(test_id: int):
    """
    Deletes the test record AND its associated scan images and result CSVs
    from the filesystem.
    """
    row = get_db().get_test(test_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Test {test_id} not found.")

    s = get_settings()
    s.current_test_id = test_id
    for key in ("input_dir", "output_dir"):
        folder = s.get(key)
        if folder and os.path.exists(folder):
            last = os.path.basename(folder)
            if last.isdigit() and int(last) == test_id:
                try:
                    shutil.rmtree(folder)
                except Exception:
                    pass

    get_db().delete_test(test_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  OMR Operations
# ═══════════════════════════════════════════════════════════════════════════════

@app.post(
    f"{API_PREFIX}/tests/{{test_id}}/upload-pdf",
    tags=["OMR Operations"],
    summary="Upload scanned PDF and convert to images",
    dependencies=[Depends(require_api_key)],
)
async def upload_pdf(test_id: int, file: UploadFile = File(...)):
    """
    Uploads a scanned PDF, converts each page to a high-resolution JPG image
    (300 DPI), and copies the OMR template files into the test input folder.

    This is an **async** endpoint — the conversion runs in the background.
    Poll `GET /tests/{id}/status` or `GET /tests/{id}/results` to check progress.
    """
    _assert_test_exists(test_id)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")

    # Save the upload to a temp file so it survives the async boundary
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        contents = await file.read()
        tmp.write(contents)
        tmp.flush()
        tmp_path = tmp.name
    finally:
        tmp.close()

    row = get_db().get_test(test_id)
    template_folder = row[3]

    _set_job(test_id, "running", "Converting PDF to images...")

    def _run():
        try:
            proc = get_processor(test_id)
            proc.process_pdf(
                tmp_path,
                template_folder,
                progress_callback=lambda msg: _set_job(test_id, "running", msg),
            )
            _set_job(test_id, "done", "PDF converted successfully.")
        except Exception as e:
            _set_job(test_id, "error", str(e))
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()

    return {"test_id": test_id, "status": "running", "message": "PDF conversion started."}


@app.post(
    f"{API_PREFIX}/tests/{{test_id}}/run",
    tags=["OMR Operations"],
    summary="Run the OMR grading engine",
    dependencies=[Depends(require_api_key)],
)
def run_omr(test_id: int, background_tasks: BackgroundTasks):
    """
    Triggers the built-in OMRChecker engine on the test's input folder.
    The graded CSV results are written to the output folder.

    The job runs asynchronously. Use `GET /tests/{id}/results` once complete.
    """
    _assert_test_exists(test_id)
    current = _jobs.get(test_id, {})
    if current.get("status") == "running":
        raise HTTPException(
            status_code=409,
            detail="A job is already running for this test. Wait for it to finish.",
        )

    _set_job(test_id, "running", "Starting OMR engine...")

    def _run():
        try:
            proc = get_processor(test_id)
            proc.run_command(
                progress_callback=lambda msg: _set_job(test_id, "running", msg)
            )
            _set_job(test_id, "done", "OMR grading completed.")
        except Exception as e:
            _set_job(test_id, "error", str(e))

    background_tasks.add_task(_run)
    return {"test_id": test_id, "status": "running", "message": "OMR grading started in the background."}


@app.get(
    f"{API_PREFIX}/tests/{{test_id}}/status",
    tags=["OMR Operations"],
    summary="Check the status of the last background job",
    response_model=RunStatus,
    dependencies=[Depends(require_api_key)],
)
def get_job_status(test_id: int):
    """Returns the current status (`running`, `done`, or `error`) of the last operation."""
    _assert_test_exists(test_id)
    job = _jobs.get(test_id)
    if not job:
        return RunStatus(test_id=test_id, status="idle", message="No job has been run yet for this test.")
    return RunStatus(test_id=test_id, **job)


@app.get(
    f"{API_PREFIX}/tests/{{test_id}}/results",
    tags=["OMR Operations"],
    summary="Get graded results as JSON",
    dependencies=[Depends(require_api_key)],
)
def get_results(test_id: int):
    """
    Returns the most recent graded CSV as a JSON array of row objects.
    Columns `input_path` and `output_path` are filtered out.
    The `file_id` column is formatted (e.g. `page_1.jpg` → `Page 1`).
    """
    _assert_test_exists(test_id)
    s = get_settings()
    s.current_test_id = test_id
    proc = PDFProcessor(s)
    output_dir = s.get("output_dir")

    csv_files = proc.get_csv_files(output_dir)
    if not csv_files:
        raise HTTPException(
            status_code=404,
            detail="No result CSV found. Run the OMR grading first.",
        )

    csv_files.sort(key=os.path.getmtime, reverse=True)
    rows = proc.read_csv(csv_files[0])

    HIDDEN = {"input_path", "output_path"}
    result = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            if k in HIDDEN:
                continue
            if k == "file_id":
                val = str(v).replace("page_", "").replace(".jpg", "").replace(".png", "").replace(".jpeg", "")
                clean["page"] = f"Page {val}"
            else:
                clean[k] = v
        result.append(clean)

    return {
        "test_id":    test_id,
        "csv_file":   os.path.basename(csv_files[0]),
        "total_rows": len(result),
        "results":    result,
    }


@app.post(
    f"{API_PREFIX}/tests/{{test_id}}/push-firestore",
    tags=["OMR Operations"],
    summary="Push graded results to Google Firestore",
    dependencies=[Depends(require_api_key)],
)
def push_to_firestore(test_id: int, background_tasks: BackgroundTasks):
    """
    Uploads the most recent result CSV to the configured Firestore collection.

    **Prerequisites:**
    - A Firestore Auth Key JSON must be set in Settings.
    - The OMR grading must have been run first.

    Records are batch-written in groups of 500 (Firestore limit).
    """
    _assert_test_exists(test_id)
    s = get_settings()
    s.current_test_id = test_id
    proc = PDFProcessor(s)
    output_dir = s.get("output_dir")

    csv_files = proc.get_csv_files(output_dir)
    if not csv_files:
        raise HTTPException(
            status_code=404,
            detail="No result CSV found. Run OMR grading first.",
        )

    csv_files.sort(key=os.path.getmtime, reverse=True)
    csv_path = csv_files[0]

    current = _jobs.get(test_id, {})
    if current.get("status") == "running":
        raise HTTPException(
            status_code=409,
            detail="Another job is already running for this test.",
        )

    _set_job(test_id, "running", "Pushing to Firestore...")

    def _push():
        try:
            uploader = FirestoreUploader(s)
            uploader.upload_csv(
                csv_path,
                progress_callback=lambda msg: _set_job(test_id, "running", msg),
            )
            _set_job(test_id, "done", f"Pushed {os.path.basename(csv_path)} to Firestore.")
        except Exception as e:
            _set_job(test_id, "error", str(e))

    background_tasks.add_task(_push)
    return {
        "test_id": test_id,
        "csv_file": os.path.basename(csv_path),
        "status":  "running",
        "message": "Firestore sync started in the background.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════

def _assert_test_exists(test_id: int):
    if not get_db().get_test(test_id):
        raise HTTPException(status_code=404, detail=f"Test {test_id} not found.")


def _check_template_exists(template_folder: str):
    templates_dir = get_settings().get("templates_dir")
    if not templates_dir:
        return  # Skip if not configured yet
    path = os.path.join(templates_dir, template_folder)
    if not os.path.exists(path):
        raise HTTPException(
            status_code=400,
            detail=f"Template folder '{template_folder}' does not exist in the templates directory.",
        )


def _set_job(test_id: int, job_status: str, message: str):
    _jobs[test_id] = {"status": job_status, "message": message}


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    sep = "-" * 60
    print("\n" + sep)
    print("  OMR Test Manager -- REST API")
    print(sep)
    print("  Swagger UI  : http://localhost:8000/docs")
    print("  ReDoc       : http://localhost:8000/redoc")
    print(f"  API Base    : http://localhost:8000{API_PREFIX}")
    print("\n  [!] Your API Key (keep this secret):")
    print(f"      {API_KEY}")
    print(sep + "\n")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
