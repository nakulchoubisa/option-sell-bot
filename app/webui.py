# app/webui.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/ui", response_class=HTMLResponse)
def ui_home(request: Request):
    return templates.TemplateResponse("ui_index.html", {"request": request, "api_key": "lmim46pxidif4lpa"})
    
