#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Phosphor Works Team
# SPDX-License-Identifier: GPL-3.0-or-later
"""The lesson index of the phosphor-works repos.

The lessons are Markdown files in the plugin's lessons/ directory, one lesson
each, with front matter. This tool builds a local SQLite index of them (a
sqlite-vec table of embeddings and an FTS5 table of the text) and searches it
with both, so a question finds a lesson by meaning and by exact symbol names.
The index is derived data: it lives outside git, in the data directory, and is
rebuilt from the files whenever they change.

  lessons.py check                       front matter of every lesson (no dependencies)
  lessons.py index                       build or update the index
  lessons.py search QUERY [--repo R] [-k N]
  lessons.py hook                        UserPromptSubmit hook: JSON in, context out

The embeddings come from a local ONNX model (fastembed). Nothing leaves the
machine. The dependencies live in a virtualenv in the data directory, which
workspace/tools/setup creates. Without it, the hook does nothing.
"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LESSONS_DIR = HERE.parent.parent / 'lessons'
DATA_DIR = Path(os.environ.get('PHOSPHOR_LESSONS_DATA')
                or Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share') / 'phosphor-works/lessons')
DB_PATH = DATA_DIR / 'lessons.db'
MODEL = 'BAAI/bge-small-en-v1.5'
DIM = 384

# A lesson reaches the prompt hook only when it is this close in meaning (cosine
# distance, 0 = same) or when the keyword search matches it too. Search on demand
# shows the best matches whatever their distance.
HOOK_MAX_DISTANCE = float(os.environ.get('PHOSPHOR_LESSONS_MAX_DISTANCE', '0.36'))
HOOK_K = 3
# How much farther a lesson may be when the keyword search matches it too.
KEYWORD_ALLOWANCE = 0.05
# How much farther than the best lesson another lesson may be, for the hook.
HOOK_SPREAD = 0.04

REQUIRED = ('id', 'title', 'repos', 'domains', 'added')
ID_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')


# --- Lesson files ----------------------------------------------------------

def parse(path):
    """Front matter and body of one lesson file. Front matter is `key: value`
    lines; a value in [brackets] is a comma-separated list."""
    text = path.read_text(encoding='utf-8')
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
    if not m:
        raise ValueError(f'{path.name}: no front matter between --- lines')
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, sep, value = line.partition(':')
        if not sep:
            raise ValueError(f'{path.name}: front matter line without a colon: {line!r}')
        value = value.strip()
        if value.startswith('[') and value.endswith(']'):
            value = [v.strip() for v in value[1:-1].split(',') if v.strip()]
        meta[key.strip()] = value
    body = re.sub(r'<!--.*?-->', '', m.group(2), flags=re.S).strip()  # the SPDX header
    return meta, body


def load_all():
    lessons, errors = [], []
    for path in sorted(LESSONS_DIR.glob('*.md')):
        try:
            meta, body = parse(path)
        except ValueError as e:
            errors.append(str(e))
            continue
        missing = [k for k in REQUIRED if not meta.get(k)]
        if missing:
            errors.append(f'{path.name}: missing {", ".join(missing)}')
            continue
        if meta['id'] != path.stem or not ID_RE.match(meta['id']):
            errors.append(f'{path.name}: id must be the file name in lowercase-with-dashes')
            continue
        for key in ('repos', 'domains'):
            if not isinstance(meta[key], list):
                errors.append(f'{path.name}: {key} must be a [list]')
        if not body:
            errors.append(f'{path.name}: no text after the front matter')
        lessons.append({'path': path, 'meta': meta, 'body': body})
    return lessons, errors


def document(lesson):
    """The text that is embedded and searched."""
    m = lesson['meta']
    return f"{m['title']}\n{lesson['body']}\nDomains: {', '.join(m['domains'])}"


# --- Index -------------------------------------------------------------------

def connect():
    import sqlite_vec
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    db.executescript(f"""
        CREATE TABLE IF NOT EXISTS lesson(
            rowid INTEGER PRIMARY KEY, id TEXT UNIQUE, hash TEXT, title TEXT, repos TEXT,
            domains TEXT, added TEXT, body TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS lesson_vec USING vec0(embedding float[{DIM}] distance_metric=cosine);
        CREATE VIRTUAL TABLE IF NOT EXISTS lesson_fts USING fts5(title, body, domains, tokenize='porter unicode61');
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    return db


_model = None


def model():
    global _model
    if _model is None:
        os.environ.setdefault('FASTEMBED_CACHE_PATH', str(DATA_DIR / 'models'))
        from fastembed import TextEmbedding
        _model = TextEmbedding(MODEL)
    return _model


def fingerprint():
    h = hashlib.sha256(MODEL.encode())
    for path in sorted(LESSONS_DIR.glob('*.md')):
        st = path.stat()
        h.update(f'{path.name}:{st.st_size}:{st.st_mtime_ns}'.encode())
    return h.hexdigest()


def update_index(db, quiet=False):
    """Bring the index in line with the lesson files. Only new or changed
    lessons are embedded again."""
    fp = fingerprint()
    row = db.execute("SELECT value FROM meta WHERE key='fingerprint'").fetchone()
    if row and row[0] == fp:
        return 0
    lessons, errors = load_all()
    for e in errors:
        print(f'lessons: skipped {e}', file=sys.stderr)
    known = {r[0]: (r[1], r[2]) for r in db.execute('SELECT id, rowid, hash FROM lesson')}
    seen, todo = set(), []
    for lesson in lessons:
        m = lesson['meta']
        doc = document(lesson)
        digest = hashlib.sha256((MODEL + doc + json.dumps(m, sort_keys=True)).encode()).hexdigest()
        seen.add(m['id'])
        if m['id'] in known and known[m['id']][1] == digest:
            continue
        todo.append((lesson, doc, digest))
    for lid, (rowid, _) in known.items():
        if lid not in seen:
            delete(db, rowid)
    if todo:
        vectors = list(model().passage_embed([doc for _, doc, _ in todo]))
        for (lesson, doc, digest), vec in zip(todo, vectors):
            m = lesson['meta']
            if m['id'] in known:
                delete(db, known[m['id']][0])
            cur = db.execute(
                'INSERT INTO lesson(id, hash, title, repos, domains, added, body) VALUES (?,?,?,?,?,?,?)',
                (m['id'], digest, m['title'], ','.join(m['repos']), ','.join(m['domains']), m['added'],
                 lesson['body']))
            rowid = cur.lastrowid
            db.execute('INSERT INTO lesson_vec(rowid, embedding) VALUES (?, ?)', (rowid, vec.astype('float32').tobytes()))
            db.execute('INSERT INTO lesson_fts(rowid, title, body, domains) VALUES (?,?,?,?)',
                       (rowid, m['title'], lesson['body'], ' '.join(m['domains'])))
    db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('fingerprint', ?)", (fp,))
    db.commit()
    if not quiet:
        print(f'lessons: {len(lessons)} indexed, {len(todo)} embedded, '
              f'{len(set(known) - seen)} removed', file=sys.stderr)
    return len(todo)


def delete(db, rowid):
    db.execute('DELETE FROM lesson WHERE rowid=?', (rowid,))
    db.execute('DELETE FROM lesson_vec WHERE rowid=?', (rowid,))
    db.execute('DELETE FROM lesson_fts WHERE rowid=?', (rowid,))


def fts_query(text):
    """An FTS5 OR query of the distinctive words of TEXT: identifiers and words
    of four letters or more, quoted so that no word is read as syntax."""
    words = re.findall(r'[A-Za-z_][A-Za-z0-9_:.-]{3,}', text)
    stop = {'this', 'that', 'with', 'from', 'what', 'when', 'have', 'does', 'into', 'then', 'them', 'they',
            'should', 'would', 'could', 'there', 'their', 'about', 'which', 'where', 'please', 'make'}
    seen, out = set(), []
    for w in words:
        lw = w.lower()
        if lw in stop or lw in seen:
            continue
        seen.add(lw)
        out.append('"' + w.replace('"', '') + '"')
    return ' OR '.join(out[:24])


def search(db, query, repo=None, k=5, max_distance=None):
    """Hybrid search: rank by vector distance and by BM25, fuse the ranks
    (reciprocal rank fusion), keep lessons for REPO or for every repo."""
    vec = list(model().query_embed([query]))[0].astype('float32').tobytes()
    pool = max(k * 4, 20)
    vrows = db.execute('SELECT rowid, distance FROM lesson_vec WHERE embedding MATCH ? AND k = ? '
                       'ORDER BY distance', (vec, pool)).fetchall()
    vrank = {r: (i, d) for i, (r, d) in enumerate(vrows)}
    frank = {}
    q = fts_query(query)
    if q:
        try:
            frows = db.execute('SELECT rowid FROM lesson_fts WHERE lesson_fts MATCH ? ORDER BY bm25(lesson_fts) '
                               'LIMIT ?', (q, pool)).fetchall()
            frank = {r[0]: i for i, r in enumerate(frows)}
        except sqlite3.OperationalError:
            frank = {}
    scored = []
    for rowid in set(vrank) | set(frank):
        dist = vrank[rowid][1] if rowid in vrank else None
        if max_distance is not None:
            # For the hook a lesson must be close in meaning. A keyword match
            # too gives it a little more room, never a place on its own.
            limit = max_distance + (KEYWORD_ALLOWANCE if rowid in frank else 0)
            if dist is None or dist > limit:
                continue
        score = (1 / (60 + vrank[rowid][0]) if rowid in vrank else 0) + (1 / (60 + frank[rowid]) if rowid in frank else 0)
        lid, title, repos, domains, body = db.execute(
            'SELECT id, title, repos, domains, body FROM lesson WHERE rowid=?', (rowid,)).fetchone()
        repo_list = [r.lower() for r in repos.split(',')]
        if repo and 'all' not in repo_list and repo.lower() not in repo_list:
            continue
        scored.append((score, dist, lid, title, repos, domains, body))
    scored.sort(key=lambda s: -s[0])
    if max_distance is not None:
        # For the hook, keep only lessons about as close as the best one, so a
        # strong match does not bring weaker neighbours with it.
        best = min((s[1] for s in scored if s[1] is not None), default=None)
        if best is not None:
            scored = [s for s in scored if s[1] <= best + HOOK_SPREAD]
    return scored[:k]


# --- Repo of the session ---------------------------------------------------------

def current_repo(cwd):
    """The repo name, as the guard picks it: the main checkout of the project."""
    start = os.environ.get('CLAUDE_PROJECT_DIR') or cwd or os.getcwd()
    try:
        common = subprocess.run(['git', '-C', start, 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                                capture_output=True, text=True, timeout=3).stdout.strip()
        if common:
            return Path(common).parent.name
    except (OSError, subprocess.SubprocessError):
        pass
    return Path(start).name


# --- Commands ----------------------------------------------------------------

def cmd_check(_):
    lessons, errors = load_all()
    ids = [l['meta']['id'] for l in lessons]
    errors += [f'duplicate id {i}' for i in sorted({i for i in ids if ids.count(i) > 1})]
    for e in errors:
        print(e)
    print(f'{len(lessons)} lessons, {len(errors)} problems')
    return 1 if errors else 0


def cmd_index(_):
    db = connect()
    update_index(db)
    return 0


def format_hit(hit, full=True):
    _, dist, lid, title, repos, domains, body = hit
    head = f'### {title}\n`{lid}` · repos: {repos} · domains: {domains}' + (f' · distance {dist:.2f}' if dist is not None else '')
    return head + ('\n\n' + body if full else '')


def cmd_search(args):
    db = connect()
    update_index(db, quiet=True)
    hits = search(db, ' '.join(args.query), repo=args.repo, k=args.k)
    if not hits:
        print('No lesson matches.')
    for h in hits:
        print(format_hit(h) + '\n')
    return 0


def cmd_hook(_):
    """UserPromptSubmit: add the lessons that match the prompt. Never blocks:
    any failure leaves the prompt as it is."""
    try:
        data = json.load(sys.stdin)
        prompt = data.get('prompt') or ''
        if len(prompt.strip()) < 12:
            return 0
        db = connect()
        update_index(db, quiet=True)
        hits = search(db, prompt[:2000], repo=current_repo(data.get('cwd')), k=HOOK_K,
                      max_distance=HOOK_MAX_DISTANCE)
        if not hits:
            return 0
        text = ('Lessons from earlier sessions that may apply (from the phosphor-works lesson index; '
                'search more with the phosphor-works:lessons skill):\n\n' + '\n\n'.join(format_hit(h) for h in hits))
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': text}}))
    except Exception as e:  # the hook must never stop a prompt
        print(f'lessons hook: {type(e).__name__}: {e}', file=sys.stderr)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('check')
    sub.add_parser('index')
    s = sub.add_parser('search')
    s.add_argument('query', nargs='+')
    s.add_argument('--repo', help='only lessons for this repo (and for every repo)')
    s.add_argument('-k', type=int, default=5)
    sub.add_parser('hook')
    args = p.parse_args()
    return {'check': cmd_check, 'index': cmd_index, 'search': cmd_search, 'hook': cmd_hook}[args.cmd](args)


if __name__ == '__main__':
    sys.exit(main())
