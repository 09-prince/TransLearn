from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend import main
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
import io
from fastapi.staticfiles import StaticFiles


app = FastAPI()
backend = main()


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MCQRequest(BaseModel):
    link: str
    num: int
    diff: str

class NotesRequest(BaseModel):
    link: str

class SummaryRequest(BaseModel):
    link: str


@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



@app.post("/mcq")
async def generate_mcq(data: MCQRequest):
    try:
        result = backend.Mcq(data.link, data.num, data.diff)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})



@app.post("/notes")
async def generate_notes(data: NotesRequest):
    try:
        pdf_bytes = backend.Notes(data.link)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=notes.pdf"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})




@app.post("/summary-audio")
async def generate_summary_audio(data: SummaryRequest):
    try:
        audio_bytes = backend.Voice(data.link)
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=summary_audio.mp3"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})














