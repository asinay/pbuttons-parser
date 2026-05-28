import uuid
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pbuttons_parser import parse_sections, build_output

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="pButtons Parser")
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory store: session_id -> (header_html, sections)
sessions: dict = {}


@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("static/index.html")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".html"):
        raise HTTPException(400, "Only .html pButtons files are supported.")

    content = await file.read()
    html = content.decode("iso-8859-1", errors="replace")

    header_html, sections = parse_sections(html)

    session_id = str(uuid.uuid4())
    sessions[session_id] = (header_html, sections)

    return {
        "session_id": session_id,
        "filename": file.filename,
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "sensitive": s.sensitive,
                "sensitive_reason": s.sensitive_reason,
            }
            for s in sections
        ],
    }


class ExportRequest(BaseModel):
    session_id: str
    selected_ids: list[str]
    output_filename: str = "pbuttons_filtered.html"


@app.post("/export")
async def export_file(req: ExportRequest):
    if req.session_id not in sessions:
        raise HTTPException(404, "Session not found. Please re-upload the file.")

    header_html, sections = sessions[req.session_id]
    output_html = build_output(header_html, sections, req.selected_ids)

    safe_name = Path(req.output_filename).name
    if not safe_name.endswith(".html"):
        safe_name += ".html"

    out_path = OUTPUT_DIR / safe_name
    out_path.write_text(output_html, encoding="iso-8859-1", errors="replace")

    return FileResponse(
        path=str(out_path),
        filename=safe_name,
        media_type="text/html",
    )
