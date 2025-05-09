from functools import lru_cache
from typing import Dict, Any

from fastapi import FastAPI, Request, Form, status, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class EmailConfig(BaseModel):
    sender_email: str = os.getenv("HOST_EMAIL")
    receiver_email: str = os.getenv("HOST_EMAIL")
    password: str = os.getenv("HOST_PASSWORD")
    smtp_server: str = 'mail.privateemail.com'
    port: int = 465

@lru_cache()
def get_email_config() -> EmailConfig:
    return EmailConfig()

def create_html_content(data: Dict[str, Any]) -> str:
    return f"""
    <html>
    <body>
        <h2>Form</h2>
        {''.join(f'<p><b>{k.title()}:</b> {v}</p>' for k, v in data.items())}
    </body>
    </html>
    """

def send_email(config: EmailConfig, subject: str, content: str):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"Ecomaritime Logistic BV <{config.sender_email}>"
    message["To"] = config.receiver_email
    message.set_content(content, subtype='html')

    with smtplib.SMTP_SSL(config.smtp_server, config.port) as server:
        server.login(config.sender_email, config.password)
        server.send_message(message)

@app.get("/")
@app.get("/about")
@app.get("/contact")
@app.get("/storage")
@app.get("/railway")
@app.get("/pipeline")
@app.get("/terminal")
@app.get("/shipping") # Add shipping route
async def render_page(request: Request):
    template = request.url.path.strip("/") or "index"
    return templates.TemplateResponse(f"{template}.html", {"request": request})

@app.post("/sendmail")
async def contact(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    subject: str = Form(...),
    email: EmailStr = Form(...),
    message: str = Form(...)
):
    config = get_email_config()
    content = create_html_content({"name": name, "email": email, "message": message})
    background_tasks.add_task(send_email, config, subject, content)
    return RedirectResponse(url="/contact", status_code=status.HTTP_302_FOUND)

@app.post("/sendquote")
async def send_quote(
    background_tasks: BackgroundTasks,
    fname: str = Form(...),
    lname: str = Form(...),
    option: str = Form(...),
    phone: str = Form(...),
    message: str = Form(...)
):
    config = get_email_config()
    subject = f"Quote Request: {option}"
    content = create_html_content({
        "name": f"{fname} {lname}",
        "phone": phone,
        "option": option,
        "message": message
    })
    background_tasks.add_task(send_email, config, subject, content)
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

@app.middleware("http")
async def add_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update({
        "X-XSS-Protection": "1; mode=block",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "public, max-age=1200" if response.status_code == 200 else "no-store"
    })
    return response

@app.middleware("http")
async def fix_mime_type(request: Request, call_next):
    response = await call_next(request)
    content_types = {".ttf": "font/ttf", ".woff": "font/woff", ".woff2": "font/woff2"}
    ext = os.path.splitext(request.url.path)[1]
    if ext in content_types:
        response.headers["Content-Type"] = content_types[ext]
    return response