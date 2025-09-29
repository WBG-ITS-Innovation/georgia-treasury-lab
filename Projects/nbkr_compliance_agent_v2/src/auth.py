import os, time, jwt
from fastapi import APIRouter, HTTPException, Form, Request, Depends
from pydantic import BaseModel

router = APIRouter(tags=["auth"])

USERS = {
    os.getenv("USER1_NAME", "alice"): {
        "password": os.getenv("USER1_PASSWORD", "secret1"),
        "role":     os.getenv("USER1_ROLE", "admin")
    },
    os.getenv("USER2_NAME", "bob"): {
        "password": os.getenv("USER2_PASSWORD", "secret2"),
        "role":     os.getenv("USER2_ROLE", "user")
    },
}

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "60"))

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: int

def make_token(sub: str, role: str) -> TokenOut:
    now = int(time.time())
    exp = now + JWT_EXPIRE_MIN * 60
    payload = {"sub": sub, "role": role, "iat": now, "exp": exp}
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return TokenOut(access_token=token, expires_at=exp)

@router.post("/token", response_model=TokenOut)
def login(username: str = Form(...), password: str = Form(...)):
    user = USERS.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return make_token(username, user["role"])

def require_user(request: Request):
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth.split(" ", 1)[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
