"""
Base classes for optimization passes and pass manager.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Type
from src.llvm.ir_nodes import IRModule, IRFunction


@dataclass
class PassResult:
    pass_name: str
    changes_made: int
    description: str
    details: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return self.changes_made > 0


class OptimizationPass(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, module: IRModule) -> PassResult:
        pass


class PassManager:
    def __init__(self):
        self.passes: List[OptimizationPass] = []
        self.pass_history: List[PassResult] = []

    def add_pass(self, opt_pass: OptimizationPass) -> "PassManager":
        self.passes.append(opt_pass)
        return self

    def clear(self):
        self.passes.clear()
        self.pass_history.clear()

    def run(self, module: IRModule, max_iterations: int = 5) -> List[PassResult]:
        """
        Runs registered passes sequentially. If any pass makes changes,
        iterates until fixed point or max_iterations reached.
        """
        all_results: List[PassResult] = []
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            iteration_changes = 0

            for opt_pass in self.passes:
                result = opt_pass.run(module)
                all_results.append(result)
                self.pass_history.append(result)
                iteration_changes += result.changes_made

            # If no changes were made across the entire pipeline, converged!
            if iteration_changes == 0:
                break

        return all_results
