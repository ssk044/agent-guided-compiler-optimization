"""Shared, persistent experiment history; opening a run never executes code."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = PROJECT_ROOT / 'reports' / 'history'


def save_experiment(result: dict, *, interface: str, source_name: str = 'program',
                    report_path=None, history_dir=None) -> str:
    root = Path(history_dir) if history_dir is not None else HISTORY_DIR
    root.mkdir(parents=True, exist_ok=True)
    run_id = uuid4().hex
    record = {'id': run_id, 'created_at': datetime.now(timezone.utc).isoformat(),
              'interface': interface, 'source_name': source_name,
              'result': {key: value for key, value in result.items() if key != 'pyc'}}
    if report_path:
        record['report_path'] = str(Path(report_path).resolve())
        record['report_text'] = Path(report_path).read_text(encoding='utf-8')
    # Replace atomically so a simultaneous browser/terminal reader sees complete records.
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=root, suffix='.tmp', delete=False) as handle:
        temporary = Path(handle.name)
        try:
            json.dump(record, handle, indent=2)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    os.replace(temporary, root / f'{run_id}.json')
    return run_id


def save_output(run_id: str, output: dict, *, history_dir=None) -> None:
    if len(run_id) != 32 or any(char not in '0123456789abcdef' for char in run_id):
        raise ValueError('Invalid experiment identifier')
    root = Path(history_dir) if history_dir is not None else HISTORY_DIR
    path = root / f'{run_id}.json'
    record = json.loads(path.read_text(encoding='utf-8'))
    record['result']['saved_output'] = output
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=root, suffix='.tmp', delete=False) as handle:
        json.dump(record, handle, indent=2)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def list_experiments(history_dir=None, *, include_legacy=True) -> list[dict]:
    root = Path(history_dir) if history_dir is not None else HISTORY_DIR
    records = []
    for path in root.glob('*.json'):
        try:
            record = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(record, dict) and isinstance(record.get('result'), dict) and record.get('id'):
                records.append(record)
        except (OSError, ValueError):
            continue
    # Earlier terminal versions already saved Markdown reports: expose those too.
    if include_legacy and history_dir is None:
        archived = {record.get('report_path') for record in records}
        for path in (PROJECT_ROOT / 'reports' / 'runs').glob('*/REPORT.md'):
            if str(path.resolve()) in archived:
                continue
            try:
                records.append({'id': str(path.relative_to(PROJECT_ROOT)),
                                'created_at': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                                'interface': 'Earlier terminal run', 'source_name': path.parent.name,
                                'result': {}, 'report_text': path.read_text(encoding='utf-8')})
            except OSError:
                continue
    return sorted(records, key=lambda record: record.get('created_at', ''), reverse=True)


def run_label(record: dict) -> str:
    timestamp = datetime.fromisoformat(record['created_at']).astimezone(ZoneInfo('Asia/Kolkata')).strftime('%d %b %Y %H:%M:%S')
    result = record['result']
    return f"{timestamp} · {result.get('language', 'C/Python')} · {result.get('model', result.get('backend', 'Saved report'))} · {record['source_name']} · {record['interface']}"


def saved_views(result: dict) -> list[tuple[str, str, str]]:
    language = result.get('language')
    views = [('Original source', result.get('source', ''), 'python' if language == 'Python' else 'c')]
    if language == 'Python':
        views += [('Bytecode before', result.get('baseline_bytecode', ''), 'text'),
                  ('Compiled bytecode', result.get('code', ''), 'text')]
    else:
        views += [('LLVM IR before', result.get('initial_ir', ''), 'llvm'),
                  ('Optimized code / LLVM IR after', result.get('code', ''), 'llvm')]
        if result.get('custom_optimizer'):
            from src.cli.run_report import render_tac
            for title, key in [('TAC before', 'initial_ir'), ('TAC after', 'code')]:
                try:
                    views.append((title, render_tac(result[key]), 'text'))
                except (ValueError, KeyError, IndexError, AttributeError):
                    pass
    return [(title, code, syntax) for title, code, syntax in views if code]


def browse_terminal(*, prompt=True, console=None):
    from rich.console import Console
    from rich.syntax import Syntax
    console = console or Console()
    if prompt:
        try:
            answer = console.input('\nView previous experiment runs before exiting? [y/N]: ')
        except EOFError:
            return
        if answer.strip().lower() not in ('y', 'yes'):
            return
    while True:
        records = list_experiments()
        if not records:
            console.print('No saved experiments yet.')
            return
        for index, record in enumerate(records, 1):
            console.print(f'{index}. {run_label(record)}', markup=False)
        try:
            choice = console.input('Enter a run number to view, or Enter to finish: ').strip()
        except EOFError:
            return
        if not choice:
            return
        if not choice.isdigit() or not 1 <= int(choice) <= len(records):
            console.print('Choose a number from the list.')
            continue
        record = records[int(choice) - 1]
        console.print(run_label(record), markup=False)
        console.print('Saved results only; this does not run the program again.')
        if record.get('report_text'):
            console.print(record['report_text'], markup=False)
        else:
            result = record['result']
            console.print(json.dumps({key: value for key, value in result.items()
                                     if key not in ('source', 'code', 'initial_ir', 'baseline_bytecode', 'fingerprint')}, indent=2), markup=False)
            for title, code, syntax in saved_views(result):
                console.print(title)
                console.print(Syntax(code, syntax, word_wrap=True))
