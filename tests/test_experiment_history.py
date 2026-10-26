import io
import tempfile
from pathlib import Path
from unittest.mock import patch
from rich.console import Console
from src.experiment_history import save_experiment, list_experiments, save_output, browse_terminal


def test_history_preserves_separate_runs_and_outputs():
    with tempfile.TemporaryDirectory() as directory:
        result = dict(language='Python', source='print(42)', code='bytecode', pyc=b'bytes')
        first = save_experiment(result, interface='Streamlit', history_dir=directory)
        second = save_experiment(result, interface='Terminal', history_dir=directory)
        assert first != second
        save_output(first, {'stdout': '42\n'}, history_dir=directory)
        (Path(directory)/'broken.json').write_text('{')
        records = list_experiments(directory)
        assert len(records) == 2
        assert {record['interface'] for record in records} == {'Streamlit', 'Terminal'}
        restored = next(record for record in records if record['id'] == first)
        assert restored['result']['source'] == 'print(42)'
        assert restored['result']['saved_output']['stdout'] == '42\n'
        assert 'pyc' not in restored['result']


def test_terminal_history_opens_snapshot_without_execution():
    with tempfile.TemporaryDirectory() as directory:
        save_experiment(dict(language='Python', source='raise RuntimeError()', code='saved bytecode'),
                        interface='Streamlit', history_dir=directory)
        records = list_experiments(directory)
        output = io.StringIO()
        console = Console(file=output)
        with patch('src.experiment_history.list_experiments', return_value=records), patch.object(console, 'input', side_effect=['1', '']):
            browse_terminal(prompt=False, console=console)
        assert 'saved bytecode' in output.getvalue()
        assert 'raise RuntimeError' in output.getvalue()
