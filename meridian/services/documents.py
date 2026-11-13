"""Authenticated private document storage with bounded text previews."""
import io
import json
import os
from pathlib import Path
import uuid
import zipfile
from xml.etree import ElementTree

from pypdf import PdfReader
from . import storage

MAX_BYTES = 10 * 1024 * 1024
SLOTS = {'resume', 'transcript', 'sop', 'lor', 'other'}
EXTENSIONS = {'.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg'}
PREVIEW_LIMIT = 2000
ANALYSIS_LIMIT = 50000


def validate(name, data):
    name = name.replace('\\', '/').rsplit('/', 1)[-1][:200]
    suffix = Path(name).suffix.lower()
    if suffix not in EXTENSIONS:
        raise ValueError('Use PDF, DOCX, TXT, PNG or JPEG.')
    if not data or len(data) > MAX_BYTES:
        raise ValueError('Choose a nonempty file up to 10 MB.')
    valid = True
    if suffix == '.pdf':
        valid = data.startswith(b'%PDF-')
    elif suffix == '.png':
        valid = data.startswith(b'\x89PNG\r\n\x1a\n')
    elif suffix in ('.jpg', '.jpeg'):
        valid = data.startswith(b'\xff\xd8\xff')
    elif suffix == '.docx':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                valid = {'[Content_Types].xml', 'word/document.xml'} <= set(archive.namelist())
        except (zipfile.BadZipFile, OSError):
            valid = False
    elif suffix == '.txt':
        try:
            data.decode('utf-8')
            valid = b'\x00' not in data
        except UnicodeDecodeError:
            valid = False
    if not valid:
        raise ValueError('The file contents do not match its format. Choose a valid file and retry.')
    return name, suffix


def extract_text(name, data):
    suffix = Path(name).suffix.lower()
    try:
        if suffix == '.txt':
            text = data.decode('utf-8')
        elif suffix == '.docx':
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                root = ElementTree.fromstring(archive.read('word/document.xml'))
            text = ' '.join(node.text or '' for node in root.iter() if node.tag.endswith('}t'))
        elif suffix == '.pdf':
            reader = PdfReader(io.BytesIO(data))
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        else:
            return ''  # No OCR is configured; image contents are not analysed.
    except (ElementTree.ParseError, OSError, ValueError, zipfile.BadZipFile) as exc:
        raise ValueError('The document text could not be extracted.') from exc
    text = ' '.join(text.split())
    return text


def extract_preview(name, data):
    text = extract_text(name, data)
    return text[:PREVIEW_LIMIT] + ('…' if len(text) > PREVIEW_LIMIT else '') if text else 'No readable text; OCR is not configured.'


def analysis_inputs(token, snapshot):
    """Read the exact saved files, not their truncated UI previews."""
    account = storage.user(token)
    evidence, texts = [], []
    for slot in sorted(SLOTS):
        identifier = snapshot.get(slot + '_id')
        if not identifier:
            continue
        item = {'slot': slot, 'name': snapshot[slot + '_name'], 'characters': 0,
                'status': 'unavailable', 'consumed_by': []}
        try:
            data = _read_blob(account['id'], identifier)
            text = extract_text(item['name'], data)
            item['characters'] = min(len(text), ANALYSIS_LIMIT)
            item['truncated'] = len(text) > ANALYSIS_LIMIT
            if text:
                texts.append(text[:ANALYSIS_LIMIT])
                item.update(status='extracted', notice='Text extracted; agent consumption is recorded separately.')
            else:
                item['notice'] = 'No readable text. Image/scanned documents require OCR, which is not configured.'
        except (OSError, ValueError) as exc:
            item['notice'] = str(exc) if isinstance(exc, ValueError) else 'Stored file could not be read. Upload it again.'
        evidence.append(item)
    return '\n'.join(texts), evidence


def _path(account_id, identifier):
    # Neither client filenames nor paths determine the private storage location.
    uuid.UUID(identifier)
    return Path(os.getenv('MERIDIAN_DATA_DIR', '.meridian')) / 'documents' / str(account_id) / identifier


def _read_blob(account_id, identifier):
    with storage.connect() as db:
        row = storage._execute(
            db, 'SELECT data FROM document_blobs WHERE user_id=? AND identifier=?',
            (account_id, identifier),
        ).fetchone()
    if row:
        value = row['data'] if isinstance(row, dict) else row[0]
        return bytes(value)
    return _path(account_id, identifier).read_bytes()


def store(token, slot, name, data):
    if slot not in SLOTS:
        raise ValueError('Unknown document slot.')
    storage.user(token)
    name, suffix = validate(name, data)
    identifier = str(uuid.uuid4())
    with storage.connect() as db:
        if not storage._postgres_url():
            db.execute('BEGIN IMMEDIATE')
        account = storage.authorized(db, token)
        docs = json.loads(account['documents'])
        old = docs.get(slot+'_id')
        path = _path(account['id'], identifier)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_bytes(data)
            preview = extract_preview(name, data)
            docs.update({slot+'_id': identifier, slot+'_name': name, slot+'_type': suffix[1:].upper(),
                         slot+'_size': f'{len(data):,} bytes', slot+'_status': 'Text extracted' if not preview.startswith('No readable text') else 'Text unavailable',
                         slot+'_preview': preview})
            storage._execute(db, "UPDATE users SET documents=?, results='{}' WHERE id=?", (json.dumps(docs), account['id']))
            storage._execute(db, 'DELETE FROM document_blobs WHERE user_id=? AND identifier=?', (account['id'], identifier))
            storage._execute(db, 'INSERT INTO document_blobs (user_id, identifier, data) VALUES (?, ?, ?)',
                            (account['id'], identifier, data))
            db.commit()
        except Exception:
            path.unlink(missing_ok=True)
            raise
        if old:
            _path(account['id'], old).unlink(missing_ok=True)
    return docs


def download(token, slot):
    account = storage.user(token)
    docs = json.loads(account['documents'])
    if slot not in SLOTS or not docs.get(slot+'_id'):
        raise ValueError('Document not found.')
    try:
        return docs[slot+'_name'], _read_blob(account['id'], docs[slot+'_id'])
    except (FileNotFoundError, ValueError):
        raise ValueError('The stored file is missing. Please upload it again.') from None


def remove(token, slot):
    if slot not in SLOTS:
        raise ValueError('Unknown document slot.')
    with storage.connect() as db:
        if not storage._postgres_url():
            db.execute('BEGIN IMMEDIATE')
        account = storage.authorized(db, token)
        docs = json.loads(account['documents'])
        identifier = docs.get(slot+'_id')
        docs = {key: value for key, value in docs.items() if not key.startswith(slot+'_')}
        storage._execute(db, "UPDATE users SET documents=?, results='{}' WHERE id=?", (json.dumps(docs), account['id']))
        if identifier:
            storage._execute(db, 'DELETE FROM document_blobs WHERE user_id=? AND identifier=?', (account['id'], identifier))
        db.commit()
        if identifier:
            _path(account['id'], identifier).unlink(missing_ok=True)
    return docs
