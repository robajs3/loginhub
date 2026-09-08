"""Odczyt (tylko do odczytu) z baz poszczególnych appek — lista userów i weryfikacja
istniejącego hasha hasła przy migracji na pierwsze logowanie w Hubie."""
import os
import psycopg2


def _connect(app_cfg):
    db_url = os.environ.get(app_cfg["db_url_env"])
    if not db_url:
        raise RuntimeError(f"Brak zmiennej {app_cfg['db_url_env']} w .env Huba")
    conn = psycopg2.connect(db_url, connect_timeout=5)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def fetch_app_users(apps_config: dict, app_slug: str):
    """Zwraca (lista_(id, display_value), error_str_or_None)."""
    app_cfg = apps_config.get(app_slug)
    if not app_cfg:
        return [], "Nieznana appka"
    table = app_cfg["users_table"]
    column = app_cfg.get("display_column", "username")
    try:
        conn = _connect(app_cfg)
        with conn.cursor() as cur:
            cur.execute(f'SELECT id, "{column}" FROM "{table}" ORDER BY id')
            rows = cur.fetchall()
        conn.close()
        return rows, None
    except Exception as e:
        return [], f"Błąd połączenia: {e}"


def fetch_password_hash(apps_config: dict, app_slug: str, local_user_id: int):
    """Zwraca password_hash (str) danego lokalnego usera w danej appce, albo None."""
    app_cfg = apps_config.get(app_slug)
    if not app_cfg:
        return None
    table = app_cfg["users_table"]
    try:
        conn = _connect(app_cfg)
        with conn.cursor() as cur:
            cur.execute(f'SELECT password_hash FROM "{table}" WHERE id = %s', (local_user_id,))
            row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def verify_against_stored_hash(password: str, stored_hash: str) -> bool:
    """Sprawdza podane hasło względem hasha appki — obsługuje Werkzeug (7 z 8 appek)
    i bcrypt (notemaster), niezależnie od tego, który mechanizm dana appka stosuje."""
    if not stored_hash:
        return False

    from werkzeug.security import check_password_hash
    try:
        if check_password_hash(stored_hash, password):
            return True
    except Exception:
        pass  # nierozpoznany format (np. bcrypt) — spróbuj dalej

    try:
        import bcrypt
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
            return True
    except Exception:
        pass

    return False
