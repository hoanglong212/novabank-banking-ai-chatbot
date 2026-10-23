"""Cookie JWT plus revocable SQLite sessions. No demo bearer-token fallback."""
import hashlib
import hmac
import secrets
import time
from functools import lru_cache

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .auth import DEMO_USERS, DemoPrincipal
from .config import setting
from .database import Database

router = APIRouter(prefix='/api/auth')
COOKIE = 'novabank_session'
HASHER = PasswordHasher()


def db():
    return Database(setting('DB_PATH', './novabank_demo.sqlite3'))


def secret():
    value = setting('JWT_SECRET')
    if len(value.encode()) < 32:
        raise HTTPException(503, 'Authentication is not configured: set a random JWT_SECRET of at least 32 bytes')
    return value


@lru_cache(maxsize=1)
def dummy_hash():
    return HASHER.hash(secrets.token_urlsafe(32))


def initialize_auth(database):
    with database.connect() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS auth_users (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, password_hash TEXT NOT NULL,
          role TEXT NOT NULL DEFAULT 'customer', active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS auth_sessions (
          id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES auth_users(id),
          expires_at INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS login_attempts (
          bucket TEXT NOT NULL, attempted_at INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_attempts_bucket ON login_attempts(bucket,attempted_at);
        ''')
        # Explicit environment seed only. Existing passwords are never overwritten.
        for user in DEMO_USERS:
            password = setting(f'DEMO_{user.id.upper()}_PASSWORD')
            if password and not conn.execute('SELECT 1 FROM auth_users WHERE id=?',(user.id,)).fetchone():
                if len(password) < 12:
                    raise ValueError('Demo seed passwords must have at least 12 characters')
                conn.execute('INSERT INTO auth_users(id,name,password_hash) VALUES (?,?,?)',
                             (user.id,user.name,HASHER.hash(password)))


def check_origin(request):
    origins = {s.strip() for s in setting('APP_ORIGINS','http://127.0.0.1:8080,http://127.0.0.1:5173,http://localhost:5173').split(',')}
    if request.headers.get('origin') not in origins:
        raise HTTPException(403, 'Untrusted request origin')


def csrf_for(sid):
    return hmac.new(secret().encode(), ('csrf:'+sid).encode(), hashlib.sha256).hexdigest()


def session_claims(request):
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, 'Sign in required')
    try:
        claims = jwt.decode(token, secret(), algorithms=['HS256'], audience='novabank-ui', issuer='novabank',
                            options={'require':['exp','iat','sub','jti']})
        if not isinstance(claims['jti'], str) or not isinstance(claims['sub'], str):
            raise ValueError('Invalid claims')
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(401, 'Session expired or invalid') from None
    with db().connect() as conn:
        row = conn.execute('''SELECT s.*,u.name,u.role FROM auth_sessions s JOIN auth_users u ON u.id=s.user_id
            WHERE s.id=? AND s.user_id=? AND s.revoked=0 AND s.expires_at>? AND u.active=1''',
            (claims['jti'],claims['sub'],int(time.time()))).fetchone()
    if not row:
        raise HTTPException(401, 'Session expired or invalid')
    return dict(row)


def current_user(request: Request) -> DemoPrincipal:
    session = session_claims(request)
    if request.method not in ('GET','HEAD','OPTIONS'):
        check_origin(request)
        supplied = request.headers.get('x-csrf-token','')
        if not hmac.compare_digest(supplied, csrf_for(session['id'])):
            raise HTTPException(403, 'Invalid CSRF token')
    accounts = next((u.accounts for u in DEMO_USERS if u.id == session['user_id']), ())
    if not accounts:
        raise HTTPException(403, 'No demo account configured')
    return DemoPrincipal(session['user_id'],session['name'],accounts)


class Login(BaseModel):
    username: str = Field(min_length=1,max_length=80)
    password: str = Field(min_length=1,max_length=256)


def session_body(row):
    return {'user':{'id':row['user_id'],'name':row['name']},
            'csrf_token':csrf_for(row['id']),'expires_at':row['expires_at']}


@router.post('/login')
def login(payload: Login, request: Request, response: Response):
    check_origin(request)
    signing_key = secret()
    username = payload.username.strip().lower()
    now = int(time.time())
    # Do not trust X-Forwarded-For without an explicitly trusted proxy configuration.
    peer = request.client.host if request.client else 'unknown'
    buckets = [(hashlib.sha256(('user:'+username).encode()).hexdigest(),5),
               (hashlib.sha256(('ip:'+peer).encode()).hexdigest(),30)]
    with db().connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('DELETE FROM login_attempts WHERE attempted_at<=?',(now-300,))
        for bucket, limit in buckets:
            count = conn.execute('SELECT COUNT(*) FROM login_attempts WHERE bucket=?',(bucket,)).fetchone()[0]
            if count >= limit:
                raise HTTPException(429,'Too many sign-in attempts; try again later',headers={'Retry-After':'300'})
        conn.executemany('INSERT INTO login_attempts VALUES (?,?)',[(b,now) for b,_ in buckets])
        user = conn.execute('SELECT * FROM auth_users WHERE id=?',(username,)).fetchone()
    try:
        valid = HASHER.verify(user['password_hash'] if user else dummy_hash(),payload.password)
    except (VerificationError, InvalidHashError):
        valid = False
    if not valid or not user or not user['active']:
        raise HTTPException(401,'Invalid username or password')
    ttl = max(60,min(int(setting('SESSION_TTL_SECONDS','3600')),86400))
    sid = secrets.token_urlsafe(32)
    expires = now+ttl
    token = jwt.encode({'sub':username,'jti':sid,'iat':now,'exp':expires,'iss':'novabank','aud':'novabank-ui'},signing_key,algorithm='HS256')
    try:
        previous = session_claims(request)
    except HTTPException:
        previous = None
    with db().connect() as conn:
        if previous:
            conn.execute('UPDATE auth_sessions SET revoked=1 WHERE id=?',(previous['id'],))
        conn.execute('INSERT INTO auth_sessions(id,user_id,expires_at) VALUES (?,?,?)',(sid,username,expires))
    response.set_cookie(COOKIE,token,max_age=ttl,httponly=True,
                        secure=setting('AUTH_COOKIE_SECURE','true').lower()=='true',samesite='lax',path='/')
    response.headers['Cache-Control'] = 'no-store'
    return session_body({'id':sid,'user_id':username,'name':user['name'],'expires_at':expires})


@router.get('/session')
def get_session(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return session_body(session_claims(request))


@router.post('/logout')
def logout(request: Request, response: Response):
    current_user(request)  # Includes origin + CSRF checks.
    session = session_claims(request)
    with db().connect() as conn:
        conn.execute('UPDATE auth_sessions SET revoked=1 WHERE id=?',(session['id'],))
    response.delete_cookie(COOKIE,path='/',httponly=True,
                           secure=setting('AUTH_COOKIE_SECURE','true').lower()=='true',samesite='lax')
    response.headers['Cache-Control'] = 'no-store'
    return {'signed_out':True}
