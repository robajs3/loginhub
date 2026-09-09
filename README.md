# Hub — centralne logowanie (SSO)

## Czym to jest

Jedna appka Flask + Postgres, która:
- trzyma **jedyne** konta z hasłami (tabela `hub_users`),
- pozwala samodzielnie założyć konto pod `/auth/register` (można wyłączyć —
  `ALLOW_REGISTRATION=false`), albo admin zakłada je ręcznie w `/admin`,
- po zalogowaniu ustawia wspólne ciasteczko `sso_session` na całym hoście (`Path=/`),
- trzyma mapowania `hub_user ↔ lokalny user_id w każdej appce` (tabela `sso_links`),
- ma panel admina do ręcznego łączenia kont (`/admin`),
- wystawia małe wewnętrzne API (`/api/resolve`), którego pytają appki: "jaki jest mój
  lokalny user_id dla tego zalogowanego człowieka?", oraz `/api/link` (`POST`), którym
  appka sama zgłasza nowo założone u siebie konto, gdy korzysta z auto-provisioningu
  (`sso_client.resolve_or_create_local_user` — patrz `INTEGRATION.md`) zamiast
  czekać na ręczne połączenie kont przez admina.

**Nie rusza** żadnej istniejącej tabeli `users` w żadnej z 8 appek — dokłada tylko
mapowanie po swojej stronie.

## 1) Wdrożenie na serwerze

```bash
# na serwerze, w katalogu docelowym np. /opt/hub
git clone ... /opt/hub    # albo scp całego folderu hub/
cd /opt/hub

cp .env.example .env
nano .env   # wypełnij WSZYSTKIE hasła i sekrety, patrz sekcja "Uzupełnij .env" niżej

# sieć do komunikacji z bazami/appkami dockerowymi (patrz krok 2)
docker network create sso_net

docker compose up -d --build
docker compose logs -f web   # sprawdź w logach wypisane hasło bootstrap admina!
```

Pierwsze uruchomienie samo tworzy tabele (`db.create_all()`) i **jedno konto admina**
(login `admin`, hasło albo z `BOOTSTRAP_ADMIN_PASSWORD` w `.env`, albo wylosowane
i wypisane w logach — sprawdź `docker compose logs web` zaraz po starcie).

Wystaw pod `/auth` przez Tailscale Funnel:

```bash
tailscale funnel --set-path=/auth --bg localhost:8011
```

Wejdź na `https://robajs-serwer-dell.tail0ffa98.ts.net/auth/admin`, zaloguj się kontem
bootstrap, od razu utwórz **swoje** konto admina z własnym hasłem i usuń/zmień hasło
bootstrap.

## 2) Podłączenie do sso_net (żeby panel admina widział userów appek dockerowych)

Panel admina łączy się **tylko do odczytu** z bazą każdej appki, żeby pokazać listę
userów do wyboru przy łączeniu kont. Wymaga to wspólnej sieci dockerowej.

Dla każdej z appek dockerowych (**zflix, easyconv, home-library, notemaster, planowiec**)
dopisz w ich `docker-compose.yml` do serwisu `db`:

```yaml
  db:
    # ... bez zmian ...
    networks:
      - default
      - sso_net

networks:
  default:
  sso_net:
    external: true
```

Potem na serwerze w katalogu każdej appki:

```bash
docker compose up -d   # dociągnie nową sieć bez przerywania działania appki
```

Appki systemd (**koloseum, gameplan**) i tak są osiągalne przez `host.docker.internal`
(już skonfigurowane w `docker-compose.yml` Huba). **filevault** ma bazę na innym hoście
LAN (`192.168.1.150`) — też już obsłużone, żadnej dodatkowej sieci nie potrzeba.

## 3) Uzupełnij .env

- `POSTGRES_PASSWORD`, `SECRET_KEY`, `SSO_SECRET` — wygeneruj losowe:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- `SSO_SECRET` — **zapisz gdzieś obok**, będzie potrzebny w `.env` każdej z 8 appek
  (ten sam string wszędzie).
- `ALLOW_REGISTRATION` — `true`/`false` (domyślnie `true`). Włącza/wyłącza publiczną
  samoobsługową rejestrację pod `/auth/register`. Hub jest wystawiony na świat przez
  Tailscale Funnel, więc jeśli chcesz, żeby konta zakładał wyłącznie admin przez
  panel `/admin`, ustaw `ALLOW_REGISTRATION=false`.
- `*_DB_URL` dla każdej appki — prawdziwe hasła z ich `.env`/`docker-compose.yml`
  (host to nazwa kontenera bazy dla appek dockerowych, `host.docker.internal` dla
  systemd, `192.168.1.150` dla filevault). Nazwy kontenerów baz na Twoim serwerze:
  `zflix-db-1`, `easyconv-db-1`, `home-library-db-1`, `notemaster_db`, `planowiec-db-1`.

## 4) Sprawdź nazwy tabel/kolumn userów

`config.py` zakłada, że każda appka ma tabelę `users` z kolumnami `id` i `username`.
Jeśli któraś appka nazywa to inaczej, popraw `users_table` w `config.py` (`APPS` dict)
dla tej appki, albo dostosuj zapytanie SQL w `admin.fetch_app_users()`.

## Co dalej

To jest sam Hub — appki jeszcze go nie używają. Następny krok: `sso_middleware.py`,
mały plik dopisywany do każdej z 8 appek, który:
1. czyta ciasteczko `sso_session`,
2. weryfikuje podpis (ten sam `SSO_SECRET`),
3. woła `GET /api/resolve?app_slug=...&hub_user_id=...` Huba (z nagłówkiem
   `X-SSO-Api-Key: <SSO_SECRET>`),
4. jeśli appka zna link — loguje lokalnie (ustawia normalną sesję Flask appki),
5. jeśli nie — pokazuje komunikat "poproś admina o połączenie konta".

Stare `/login` w każdej appce **zostaje aktywne** jako plan B, dopóki nie potwierdzisz,
że SSO działa niezawodnie na wszystkich 8.
