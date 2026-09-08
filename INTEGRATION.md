# Integracja SSO w 8 appkach

## Zasada działania (skrót)

1. Kopiujesz `sso_client.py` do katalogu appki (obok `app.py`).
2. Dopisujesz `@app.before_request`, który: jeśli user NIE jest zalogowany lokalnie,
   pyta `sso_client.resolve_local_user_id(app_slug=...)`. Jeśli dostanie ID —
   loguje lokalnie (swoim własnym mechanizmem: `login_user()` albo `session[...]`).
3. Appka **nie rusza** hasła, tabeli `users`, ani niczego innego — SSO tylko
   "podszywa się" pod normalne zalogowanie, appka o tym nie wie.
4. Stary `/login` appki **zostaje aktywny** jako plan B — to tylko dodatkowa,
   automatyczna ścieżka logowania, nie zamiennik.

## Wymagane zmienne środowiskowe (`.env` każdej appki)

```
SSO_SECRET=<DOKŁADNIE TA SAMA WARTOŚĆ co w .env LoginHub>
HUB_INTERNAL_URL=http://127.0.0.1:8011      # appki systemd (filevault, koloseum, gameplan)
# LUB dla appek dockerowych podłączonych do sso_net:
HUB_INTERNAL_URL=http://hub-web:8000
```

## Appki dockerowe: dodatkowy krok sieciowy

Wcześniej podłączyłeś serwis **`db`** każdej appki do `sso_net` (żeby panel admina
LoginHub mógł czytać userów). Teraz **serwis `web`** też musi dołączyć do `sso_net`,
żeby appka mogła zapytać LoginHub o `/api/resolve`:

```yaml
  web:
    # ... bez zmian ...
    networks:
      - default
      - sso_net
```
(sekcja `networks:` na dole pliku z `sso_net: {external: true}` już tam jest od
poprzedniej zmiany).

## `requests` w zależnościach

Dodaj `requests` do `requirements.txt` każdej appki (jeśli go tam jeszcze nie ma).

---

## FileVault (sesja własna, nie Flask-Login)

`services/auth_service.py` używa `session["user_id"] = user.id`. W `app.py`, w
`create_app()`, przed `return app`:

```python
import sso_client
from flask import session

@app.before_request
def _sso_autologin():
    if session.get("user_id"):
        return
    local_id = sso_client.resolve_local_user_id(app_slug="filevault")
    if local_id:
        session["user_id"] = local_id
```

## Koloseum (Flask-Login)

W `app.py`, w `create_app()`, przed `return app` (User już zaimportowany z `models`):

```python
import sso_client
from flask_login import current_user, login_user

@app.before_request
def _sso_autologin():
    if current_user.is_authenticated:
        return
    local_id = sso_client.resolve_local_user_id(app_slug="koloseum")
    if local_id:
        user = User.query.get(local_id)
        if user:
            login_user(user)
```

## zFlix (Flask-Login)

W `app.py`, w `create_app()` (User już zaimportowany z `models`):

```python
import sso_client
from flask_login import current_user, login_user

@app.before_request
def _sso_autologin():
    if current_user.is_authenticated:
        return
    local_id = sso_client.resolve_local_user_id(app_slug="zflix")
    if local_id:
        user = User.query.get(local_id)
        if user:
            login_user(user)
```

## EasyConv (Flask-Login)

`app/auth.py` ma już `login_user`. W `app/__init__.py` (fabryka aplikacji), dodaj
import `User` z odpowiedniego modułu modeli i:

```python
import sso_client
from flask_login import current_user, login_user
from app.models import User  # dopasuj import do realnej struktury

@app.before_request
def _sso_autologin():
    if current_user.is_authenticated:
        return
    local_id = sso_client.resolve_local_user_id(app_slug="easyconv")
    if local_id:
        user = User.query.get(local_id)
        if user:
            login_user(user)
```

## Home Library (Flask-Login)

W `app/__init__.py`, obok istniejącego `PrefixMiddleware`:

```python
import sso_client
from flask_login import current_user, login_user
from .models import User  # dopasuj import do realnej struktury

@app.before_request
def _sso_autologin():
    if current_user.is_authenticated:
        return
    local_id = sso_client.resolve_local_user_id(app_slug="homelibrary")
    if local_id:
        user = User.query.get(local_id)
        if user:
            login_user(user)
```

## NoteMaster (Flask-Login + bcrypt — bcrypt dotyczy tylko JEJ WŁASNEGO logowania,
## nie SSO, więc integracja wygląda identycznie jak wszędzie indziej)

W `app/__init__.py`:

```python
import sso_client
from flask_login import current_user, login_user
from app.models import User  # dopasuj import

@app.before_request
def _sso_autologin():
    if current_user.is_authenticated:
        return
    local_id = sso_client.resolve_local_user_id(app_slug="notemaster")
    if local_id:
        user = User.query.get(local_id)
        if user:
            login_user(user)
```

## GamePlan (Flask-Login)

W `app.py`, w `create_app()` (User już zaimportowany z `models`):

```python
import sso_client
from flask_login import current_user, login_user

@app.before_request
def _sso_autologin():
    if current_user.is_authenticated:
        return
    local_id = sso_client.resolve_local_user_id(app_slug="gameplan")
    if local_id:
        user = User.query.get(local_id)
        if user:
            login_user(user)
```

## Planowiec (Flask-Login)

W `app.py`, w `create_app()`, zaimportuj `User` z `models.user_model`:

```python
import sso_client
from flask_login import current_user, login_user
from models.user_model import User  # dopasuj import do realnej struktury

@app.before_request
def _sso_autologin():
    if current_user.is_authenticated:
        return
    local_id = sso_client.resolve_local_user_id(app_slug="planowiec")
    if local_id:
        user = User.query.get(local_id)
        if user:
            login_user(user)
```

---

## Kolejność wdrożenia (bezpiecznie, appka po appce)

1. Skopiuj `sso_client.py` do appki, dopisz zmienne `.env`, dodaj `requests`
   do `requirements.txt`.
2. Dopisz `@app.before_request` z listy wyżej.
3. Zrestartuj appkę (`docker compose up -d --build` albo `systemctl restart ...`).
4. Wyloguj się z tej appki lokalnie, wejdź na nią ponownie (bez podawania hasła)
   — jeśli masz ważne ciasteczko `sso_session` z LoginHub (byłeś zalogowany na
   `/auth`) i Twoje konto jest połączone z tą appką w panelu — powinieneś
   automatycznie wylądować zalogowany.
5. Jeśli coś nie zadziała — appka po prostu pokaże normalny `/login` (nic się
   nie psuje), sprawdź logi appki pod kątem błędów importu/połączenia z LoginHub.
6. Dopiero po potwierdzeniu na jednej appce, powtórz na kolejnych.
