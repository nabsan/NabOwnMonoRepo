from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeSerializer, BadSignature
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import os
import json
import uuid

load_dotenv()

# 複数ユーザーの認証情報を読み込み
USERS_STR = os.getenv("USERS", "user1:password1")
VALID_USERS = {}
for user_pair in USERS_STR.split(","):
    username, password = user_pair.strip().split(":")
    VALID_USERS[username] = password

SECRET_KEY = os.getenv("SECRET_KEY")
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "data"))
RESULTS_DIR.mkdir(exist_ok=True)

serializer = URLSafeSerializer(SECRET_KEY, salt="flashrace")

WORDS_DIR = Path("words")
WORDS_DIR.mkdir(exist_ok=True)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

def auth(request: Request):
    c = request.cookies.get("session")
    if not c:
        raise HTTPException(401)
    try:
        session_data = serializer.loads(c)
        return session_data
    except BadSignature:
        raise HTTPException(401)

@app.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_post(username: str = Form(...), password: str = Form(...)):
    if username in VALID_USERS and VALID_USERS[username] == password:
        res = RedirectResponse("/", status_code=303)
        res.set_cookie("session", serializer.dumps({"username": username}), httponly=True)
        return res
    raise HTTPException(403)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    try:
        auth(request)
    except HTTPException:
        return RedirectResponse("/login", status_code=303)
    lists = [p.stem for p in WORDS_DIR.glob("*.txt")]
    return templates.TemplateResponse("index.html", {"request": request, "lists": lists})

@app.get("/game/{name}", response_class=HTMLResponse)
def game(request: Request, name: str):
    auth(request)
    return templates.TemplateResponse("game.html", {"request": request, "name": name})

@app.get("/api/words/{name}")
def words_api(request: Request, name: str):
    auth(request)
    path = WORDS_DIR / f"{name}.txt"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        w,r,m = [x.strip() for x in line.split("|")]
        rows.append({"word":w,"reading":r,"meaning":m})
    return rows

@app.post("/api/results")
def save_results(request: Request, data: dict):
    session_data = auth(request)
    username = session_data.get("username", "unknown")
    
    result_id = str(uuid.uuid4())
    # total_time_ms が送られてくる場合はそれを使い、なければresults内のtime_msを合計する
    results_list = data.get("results", [])
    total_ms = data.get("total_time_ms")
    if total_ms is None:
        total_ms = sum((int(r.get("time_ms", 0)) for r in results_list))

    result_data = {
        "id": result_id,
        "username": username,
        "timestamp": datetime.now().isoformat(),
        "list": data.get("list"),
        "results": results_list,
        "total_time_ms": int(total_ms),
        "total_time_seconds": round(int(total_ms)/1000.0, 3)
    }
    
    # 結果ファイルを保存
    result_file = RESULTS_DIR / f"{result_id}.json"
    result_file.write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return {"id": result_id}

@app.get("/results/{result_id}", response_class=HTMLResponse)
def show_results(request: Request, result_id: str):
    auth(request)
    result_file = RESULTS_DIR / f"{result_id}.json"
    if not result_file.exists():
        raise HTTPException(404)
    
    result_data = json.loads(result_file.read_text(encoding="utf-8"))
    
    # 集計
    total = len(result_data["results"])
    know = sum(1 for r in result_data["results"] if r["answer"] == "知ってる")
    dont_know = total - know
    total_time_seconds = result_data.get("total_time_seconds")
    
    return templates.TemplateResponse("results.html", {
        "request": request,
        "result_id": result_id,
        "list_name": result_data["list"],
        "total": total,
        "know": know,
        "dont_know": dont_know,
        "total_time_seconds": total_time_seconds,
        "results": result_data["results"]
    })

@app.get("/ranking", response_class=HTMLResponse)
def show_ranking(request: Request):
    auth(request)
    
    # 全ての結果ファイルを読み込み
    all_results = []
    for result_file in RESULTS_DIR.glob("*.json"):
        try:
            result_data = json.loads(result_file.read_text(encoding="utf-8"))
            total = len(result_data.get("results", []))
            know = sum(1 for r in result_data.get("results", []) if r["answer"] == "知ってる")
            total_time_ms = int(result_data.get("total_time_ms", sum((int(r.get("time_ms",0)) for r in result_data.get("results",[])))))
            total_time_sec = round(total_time_ms/1000.0, 3)
            
            all_results.append({
                "username": result_data.get("username", "unknown"),
                "list": result_data.get("list"),
                "know": know,
                "total": total,
                "total_time_ms": total_time_ms,
                "total_time_sec": total_time_sec,
                "timestamp": result_data.get("timestamp"),
                "avg_time_sec": round((total_time_sec / total), 3) if total > 0 else None
            })
        except:
            pass
    
    # 総合時間（小さい方が上位）でソート、同じ時間なら古い記録を上位に
    ranking = sorted(all_results, key=lambda x: (x.get("total_time_ms", 10**12), x.get("timestamp")))[:10]
    
    return templates.TemplateResponse("ranking.html", {
        "request": request,
        "ranking": ranking
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
