"""Private SQLite persistence with Argon2 passwords and hashed expiring sessions."""
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

HASHER = PasswordHasher()

def _postgres_url():
    return os.environ.get('MERIDIAN_DATABASE_URL', '').strip()


def _sql(statement):
    return statement.replace('?', '%s') if _postgres_url() else statement


def _execute(db, statement, params=()):
    return db.execute(_sql(statement), params)


@contextmanager
def connect():
    database_url = _postgres_url()
    if database_url:
        import psycopg
        from psycopg.rows import dict_row

        db = psycopg.connect(database_url, row_factory=dict_row)
        db.execute('''
          CREATE TABLE IF NOT EXISTS users (id BIGSERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, profile TEXT NOT NULL DEFAULT '{}',
            documents TEXT NOT NULL DEFAULT '{}', results TEXT NOT NULL DEFAULT '{}');
          CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id BIGINT REFERENCES users(id), expires DOUBLE PRECISION NOT NULL);
          CREATE TABLE IF NOT EXISTS attempts (email TEXT PRIMARY KEY, count INTEGER, reset DOUBLE PRECISION);
          CREATE TABLE IF NOT EXISTS analysis_runs (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id), agent TEXT NOT NULL,
            status TEXT NOT NULL, started_at DOUBLE PRECISION NOT NULL, completed_at DOUBLE PRECISION,
            error TEXT, result TEXT
          );
        ''')
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        return

    root = Path(os.environ.get('MERIDIAN_DATA_DIR', '.meridian'))
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / 'accounts.sqlite3', timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript('''
      CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, profile TEXT NOT NULL DEFAULT '{}',
        documents TEXT NOT NULL DEFAULT '{}', results TEXT NOT NULL DEFAULT '{}');
      CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER, expires REAL NOT NULL);
      CREATE TABLE IF NOT EXISTS attempts (email TEXT PRIMARY KEY, count INTEGER, reset REAL);
      CREATE TABLE IF NOT EXISTS analysis_runs (
        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, agent TEXT NOT NULL,
        status TEXT NOT NULL, started_at REAL NOT NULL, completed_at REAL,
        error TEXT, result TEXT
      );
    ''')
    try:
        with db:
            yield db
    finally:
        db.close()


def valid_email(email):
    return bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email)) and len(email) <= 254


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(email, password, register=False, name=''):
    email = email.strip().lower()
    if not valid_email(email):
        raise ValueError('Enter a valid email address.')
    if len(password) > 128 or (register and len(password) < 12):
        raise ValueError('Use a password between 12 and 128 characters.')
    with connect() as db:
        attempt = _execute(db, 'SELECT * FROM attempts WHERE email=?', (email,)).fetchone()
        if attempt and attempt['reset'] > time.time() and attempt['count'] >= 8:
            raise ValueError('Too many attempts. Try again in 15 minutes.')
        if register:
            if not name.strip():
                raise ValueError('Enter your name.')
            try:
                _execute(db, 'INSERT INTO users(email,password,profile) VALUES(?,?,?)',
                           (email, HASHER.hash(password), json.dumps({'email': email, 'full_name': name.strip()})))
            except sqlite3.IntegrityError:
                raise ValueError('Unable to register this email. Try signing in.') from None
        row = _execute(db, 'SELECT * FROM users WHERE email=?', (email,)).fetchone()
        try:
            HASHER.verify(row['password'] if row else HASHER.hash(secrets.token_hex(16)), password)
        except (VerificationError, InvalidHashError):
            count = attempt['count'] + 1 if attempt and attempt['reset'] > time.time() else 1
            if _postgres_url():
                _execute(db, 'INSERT INTO attempts(email,count,reset) VALUES(?,?,?) ON CONFLICT(email) DO UPDATE SET count=EXCLUDED.count, reset=EXCLUDED.reset',
                         (email, count, time.time()+900))
            else:
                _execute(db, 'INSERT OR REPLACE INTO attempts VALUES(?,?,?)', (email, count, time.time()+900))
            db.commit()
            raise ValueError('Invalid email or password.') from None
        if row is None:
            raise ValueError('Invalid email or password.')
        _execute(db, 'DELETE FROM attempts WHERE email=?', (email,))
        token = secrets.token_urlsafe(32)
        _execute(db, 'DELETE FROM sessions WHERE expires<?', (time.time(),))
        _execute(db, 'INSERT INTO sessions VALUES(?,?,?)', (digest(token), row['id'], time.time()+86400))
        return token


def user(token):
    if not token:
        raise ValueError('Please sign in to continue.')
    with connect() as db:
        return dict(authorized(db, token))


def authorized(db, token):
    row = _execute(db, 'SELECT users.* FROM users JOIN sessions ON users.id=sessions.user_id WHERE token=? AND expires>?',
                     (digest(token), time.time())).fetchone()
    if row is None:
        raise ValueError('Your session has expired. Please sign in.')
    return dict(row)


def save(token, column, value):
    if column not in ('profile', 'documents', 'results'):
        raise ValueError('Invalid storage field')
    with connect() as db:
        if not _postgres_url():
            db.execute('BEGIN IMMEDIATE')
        account = authorized(db, token)
        _execute(db, f'UPDATE users SET {column}=? WHERE id=?', (json.dumps(value), account['id']))


def save_profile(token, profile, expected):
    """Atomic optimistic update: stale tabs cannot overwrite another tab's save."""
    from ..data.profile import empty_profile
    with connect() as db:
        if not _postgres_url():
            db.execute('BEGIN IMMEDIATE')
        account = authorized(db, token)
        previous = {**empty_profile(), **json.loads(account['profile'])}
        if previous != expected:
            raise ValueError('Your profile changed in another tab. Cancel to reload it before editing again.')
        if previous != profile:
            _execute(db, 'UPDATE users SET profile=?, results=? WHERE id=?', (json.dumps(profile), '{}', account['id']))


def save_results(token, profile, results, expected_documents=None):
    from ..data.profile import empty_profile
    with connect() as db:
        if not _postgres_url():
            db.execute('BEGIN IMMEDIATE')
        account = authorized(db, token)
        if {**empty_profile(), **json.loads(account['profile'])} != profile:
            raise ValueError('Profile changed. Run analysis again for the saved profile.')
        if expected_documents is not None and json.loads(account['documents']) != expected_documents:
            raise ValueError('Documents changed. Run analysis again for the saved documents.')
        _execute(db, 'UPDATE users SET results=? WHERE id=?', (json.dumps(results), account['id']))


def record_analysis_event(token, agent, status, started_at, completed_at=None, error="", result=None):
    with connect() as db:
        account = authorized(db, token)
        _execute(db,
            'INSERT INTO analysis_runs(user_id,agent,status,started_at,completed_at,error,result) VALUES(?,?,?,?,?,?,?)',
            (account['id'], agent, status, started_at, completed_at, error, json.dumps(result) if result is not None else None),
        )


def analysis_history(token, limit=20):
    with connect() as db:
        account = authorized(db, token)
        rows = _execute(db,
            'SELECT agent,status,started_at,completed_at,error,result FROM analysis_runs '
            'WHERE user_id=? ORDER BY id DESC LIMIT ?', (account['id'], limit),
        ).fetchall()
        return [dict(row) for row in rows]


def logout(token):
    with connect() as db:
        _execute(db, 'DELETE FROM sessions WHERE token=?', (digest(token),))
