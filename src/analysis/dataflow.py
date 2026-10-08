"""
Data-flow analysis: Def-Use chains, Liveness Analysis, and Memory Alias tracking.
"""
from typing import Dict, List, Set, Tuple
from src.analysis.cfg import ControlFlowGraph
from src.llvm.ir_nodes import IRFunction, IRBasicBlock, IRInstruction


class DefUseAnalysis:
    def __init__(self, function: IRFunction):
        self.function = function
        self.def_to_uses: Dict[str, List[IRInstruction]] = {}
        self.use_to_def: Dict[str, IRInstruction] = {}
        self._compute_chains()

    def _compute_chains(self):
        # 1. Collect definitions
        for block in self.function.blocks:
            for inst in block.instructions:
                if inst.result:
                    self.use_to_def[inst.result] = inst
                    self.def_to_uses[inst.result] = []

        # 2. Collect uses
        for block in self.function.blocks:
            for inst in block.instructions:
                for used_var in inst.get_used_variables():
                    if used_var in self.def_to_uses:
                        self.def_to_uses[used_var].append(inst)

    def get_users(self, var_name: str) -> List[IRInstruction]:
        return self.def_to_uses.get(var_name, [])

    def get_def(self, var_name: str) -> IRInstruction:
        return self.use_to_def.get(var_name)

    def is_dead(self, var_name: str) -> bool:
        """Returns True if the variable is defined but has no uses."""
        return var_name in self.def_to_uses and len(self.def_to_uses[var_name]) == 0


class LivenessAnalysis:
    def __init__(self, cfg: ControlFlowGraph):
        self.cfg = cfg
        self.use: Dict[str, Set[str]] = {}
        self.defs: Dict[str, Set[str]] = {}
        self.live_in: Dict[str, Set[str]] = {}
        self.live_out: Dict[str, Set[str]] = {}
        self._compute_local_sets()
        self._compute_liveness()

    def _compute_local_sets(self):
        for name, node in self.cfg.nodes.items():
            used = set()
            defined = set()
            for inst in node.block.instructions:
                # Any variable used that hasn't been defined locally yet
                for u in inst.get_used_variables():
                    if u not in defined:
                        used.add(u)
                if inst.result:
                    defined.add(inst.result)
            self.use[name] = used
            self.defs[name] = defined
            self.live_in[name] = set()
            self.live_out[name] = set()

    def _compute_liveness(self):
        """Backwards dataflow iterative fixed-point algorithm."""
        nodes = list(self.cfg.nodes.keys())
        changed = True
        while changed:
            changed = False
            # Traverse reverse topological or reversed list
            for name in reversed(nodes):
                node = self.cfg.nodes[name]
                # OUT[B] = Union(IN[S]) for S in Succ(B)
                new_out = set()
                for succ in node.successors:
                    if succ in self.live_in:
                        new_out |= self.live_in[succ]

                # IN[B] = USE[B] U (OUT[B] - DEF[B])
                new_in = self.use[name] | (new_out - self.defs[name])

                if new_out != self.live_out[name] or new_in != self.live_in[name]:
                    self.live_out[name] = new_out
                    self.live_in[name] = new_in
                    changed = True


class MemoryTracker:
    """Tracks alloca memory slots and their associated stores and loads."""
    def __init__(self, function: IRFunction):
        self.function = function
        self.allocas: Set[str] = set() # e.g. "%a", "%b"
        self.alloca_stores: Dict[str, List[IRInstruction]] = {}
        self.alloca_loads: Dict[str, List[IRInstruction]] = {}
        self._analyze()

    def _analyze(self):
        for block in self.function.blocks:
            for inst in block.instructions:
                if inst.opcode == "alloca" and inst.result:
                    self.allocas.add(inst.result)
                    self.alloca_stores[inst.result] = []
                    self.alloca_loads[inst.result] = []

        for block in self.function.blocks:
            for inst in block.instructions:
                if inst.opcode == "store" and len(inst.operands) >= 2:
                    ptr_var = inst.operands[1].value
                    if ptr_var in self.allocas:
                        self.alloca_stores[ptr_var].append(inst)
                elif inst.opcode == "load" and inst.operands:
                    ptr_var = inst.operands[0].value
                    if ptr_var in self.allocas:
                        self.alloca_loads[ptr_var].append(inst)
