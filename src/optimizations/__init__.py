from src.optimizations.base import OptimizationPass, PassResult, PassManager
from src.optimizations.constant_folding import ConstantFoldingPass
from src.optimizations.constant_propagation import ConstantPropagationPass
from src.optimizations.dead_code_elimination import DeadCodeEliminationPass
from src.optimizations.common_subexpression_elimination import CommonSubexpressionEliminationPass
from src.optimizations.strength_reduction import StrengthReductionPass
from src.optimizations.loop_invariant_code_motion import LoopInvariantCodeMotionPass

PASS_REGISTRY = {
    "ConstantFolding": ConstantFoldingPass,
    "ConstantPropagation": ConstantPropagationPass,
    "DeadCodeElimination": DeadCodeEliminationPass,
    "CommonSubexpressionElimination": CommonSubexpressionEliminationPass,
    "StrengthReduction": StrengthReductionPass,
    "LoopInvariantCodeMotion": LoopInvariantCodeMotionPass,
}

__all__ = [
    "OptimizationPass", "PassResult", "PassManager",
    "ConstantFoldingPass", "ConstantPropagationPass",
    "DeadCodeEliminationPass", "CommonSubexpressionEliminationPass",
    "StrengthReductionPass", "LoopInvariantCodeMotionPass",
    "PASS_REGISTRY"
]
