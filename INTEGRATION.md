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

## VM Portal (Flask-Login, slug `vmportal`, prefiks `/vmka1`)

Zintegrowany jak Koloseum (`resolve_or_create_local_user`), z jedną różnicą: **nowe konta
założone przez SSO nie mają dostępu do maszyn**, dopóki admin VM Portalu nie zatwierdzi ich
w `/vmka1/admin` (flaga `users.is_allowed`; admin = `ADMIN_USERNAME` ma dostęp zawsze).

Po stronie Huba:
- w `.env` dopisz `VMPORTAL_DB_URL=postgresql://vmportal_app:<haslo>@vmportal-postgres:5432/app_db`
  (wpis `vmportal` w `APPS` w `config.py` już jest),
- kontener `vmportal-postgres` musi być w sieci `sso_net` (zrobione w `docker-compose.yml` VM Portalu).

Po stronie VM Portalu (`.env` obok `docker-compose.yml`): `SSO_SECRET` (ten sam co w Hubie)
i opcjonalnie `HUB_INTERNAL_URL` (domyślnie `http://hub-web:8000`). Serwisy `flask` i `postgres`
dołączają do `sso_net`.

Uwaga: nazwa użytkownika `ADMIN_USERNAME` w VM Portalu powinna być identyczna z loginem admina
w Hubie — konto w Hubie o tej nazwie dostaje uprawnienia admina VM Portalu.

---

## Automatyczne zakładanie konta przy pierwszej wizycie w niepodłączonej appce

Domyślnie (`resolve_local_user_id`) appka loguje przez SSO **tylko** jeśli admin
wcześniej ręcznie sparował konta w `/admin`. Jeśli zamiast tego chcesz, żeby wejście
zalogowanego (na `/auth`) użytkownika do appki, z którą jeszcze nie ma połączenia,
od razu zakładało mu tam nowe konto — użyj `sso_client.resolve_or_create_local_user`
zamiast `resolve_local_user_id`. Różnica: dajesz jej dodatkowo funkcję `create_user`,
która Twoim, appkowym mechanizmem zakłada nowego usera i zwraca jego ID.

Przykład dla Koloseum (Flask-Login, `User` z polami `username`, `password_hash`):

```python
import secrets
import sso_client
from flask_login import current_user, login_user
from models import db, User

def _create_koloseum_user(hub_username: str):
    # get-or-create po username, żeby powtórne wywołanie (np. gdy zgłoszenie do
    # Huba nie doszło za pierwszym razem) nie tworzyło duplikatu
    existing = User.query.filter_by(username=hub_username).first()
    if existing:
        return existing.id, existing.username

    username = hub_username
    suffix = 1
    while User.query.filter_by(username=username).first():
        suffix += 1
        username = f"{hub_username}{suffix}"

    user = User(username=username)
    user.set_password(secrets.token_urlsafe(24))  # losowe, nieużywane hasło — logowanie idzie przez SSO
    db.session.add(user)
    db.session.commit()
    return user.id, user.username

@app.before_request
def _sso_autologin():
    if current_user.is_authenticated:
        return
    local_id = sso_client.resolve_or_create_local_user(app_slug="koloseum", create_user=_create_koloseum_user)
    if local_id:
        user = User.query.get(local_id)
        if user:
            login_user(user)
```

Ten sam schemat (funkcja `create_user` dopasowana do Twojego modelu + wywołanie
`resolve_or_create_local_user` zamiast `resolve_local_user_id`) podmieniasz w
dowolnej z appek wyżej. Rzeczy do dopilnowania przy pisaniu `create_user`:

- **Hasło**: ustaw losowe/nieużywalne (`secrets.token_urlsafe(...)`, zahaszowane
  Twoim mechanizmem) — konto i tak zawsze będzie logowane przez SSO. Jeśli appka
  ma dodatkowo swój stary `/login` jako plan B (patrz punkt 4 na górze pliku),
  użytkownik może później samodzielnie ustawić sobie hasło przez appkowy "zapomniałem
  hasła", jeśli appka to obsługuje.
- **Kolizja nazw/e-maili**: jeśli appka wymaga unikalnego `username`/`email`, a taki
  już lokalnie istnieje (ale nie jest jeszcze podpięty pod SSO — patrz niżej),
  dopisz sufiks jak w przykładzie, zamiast wybuchać błędem unikalności.
- **Idempotencja**: rób `create_user` jako "get-or-create" (najpierw sprawdź, czy
  user o takim username/emailu już jest), bo jeśli zgłoszenie `/api/link` do Huba
  nie dojdzie (np. chwilowy problem sieciowy), kolejny request wywoła `create_user`
  ponownie.
- **Appka nie zna hub_user_id** — dostaje tylko `hub_username` (login z Huba). To
  celowe: appka i tak później dostanie swój lokalny `local_user_id` z powrotem od
  Huba przy każdym kolejnym `/api/resolve`.
- To NIE nadpisuje istniejących kont: jeśli user w danej appce już ma konto
  założone "ręcznie" (sprzed SSO) i admin je połączył w `/admin`, `resolve_or_create_local_user`
  zwróci istniejące połączenie i `create_user` w ogóle się nie wywoła.

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
