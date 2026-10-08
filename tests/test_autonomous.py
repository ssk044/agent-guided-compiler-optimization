import os
import tempfile

from src.agent.autonomous import AutonomousOrchestrator
from src.dataset import DatasetGenerator, CATEGORY_COUNTS


def test_dataset_generator_creates_requested_population():
    with tempfile.TemporaryDirectory() as directory:
        paths = DatasetGenerator(directory).generate()
        assert len(paths) == sum(CATEGORY_COUNTS.values()) == 500
        assert all(os.path.exists(path) for path in paths)


def test_autonomous_orchestrator_never_accepts_unverified_change():
    code = "#include <stdio.h>\nint main(int argc,char**argv){int x=2+3; printf(\"%d\\n\",x); return 0;}\n"
    with tempfile.TemporaryDirectory() as directory:
        source = os.path.join(directory, "demo.c")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write(code)
        run = AutonomousOrchestrator(max_iterations=2).optimize_file(source)
        assert all(not (d.decision == "accepted" and not d.verified) for d in run.decisions)
        assert run.final_cost.weighted_cost <= run.initial_cost.weighted_cost
