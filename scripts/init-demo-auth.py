"""Generate missing local demo auth values in ignored backend/.env without printing secrets."""
from pathlib import Path
import secrets
from dotenv import dotenv_values, set_key

root = Path(__file__).resolve().parents[1]
path = root/'backend/.env'
if not path.exists():
    path.touch()
values = dotenv_values(path)
for key in ('JWT_SECRET','DEMO_ALICE_PASSWORD','DEMO_BOB_PASSWORD'):
    if not values.get(key):
        set_key(path,key,secrets.token_urlsafe(48 if key=='JWT_SECRET' else 18))
if 'AUTH_COOKIE_SECURE' not in values:
    set_key(path,'AUTH_COOKIE_SECURE','false')
if not values.get('APP_ORIGINS'):
    set_key(path,'APP_ORIGINS','http://127.0.0.1:8080,http://127.0.0.1:5173,http://localhost:5173')
print('Local authentication configuration saved to backend/.env. No secrets printed.')
print('Existing users/passwords are never reset. For HTTPS set AUTH_COOKIE_SECURE=true and APP_ORIGINS explicitly.')
