"""
Dead-Code Elimination (DCE) Optimization Pass.
Removes unused pure instructions, unreferenced allocas/stores, and unreachable blocks.
"""
from typing import Set, List
from src.optimizations.base import OptimizationPass, PassResult
from src.llvm.ir_nodes import IRModule, IRFunction, IRInstruction
from src.analysis.dataflow import DefUseAnalysis, MemoryTracker
from src.analysis.cfg import ControlFlowGraph


class DeadCodeEliminationPass(OptimizationPass):
    def __init__(self):
        super().__init__("DeadCodeElimination")

    def run(self, module: IRModule) -> PassResult:
        changes = 0
        details = []

        for func in module.functions:
            if func.is_declaration:
                continue

            # 1. Eliminate unreachable basic blocks
            cfg = ControlFlowGraph(func)
            unreachable = cfg.get_unreachable_blocks()
            if unreachable:
                func.blocks = [b for b in func.blocks if b.name not in unreachable]
                changes += len(unreachable)
                details.append(f"Removed {len(unreachable)} unreachable block(s): {sorted(unreachable)}")

            # 2. Iterate dead instruction elimination
            func_changed = True
            while func_changed:
                func_changed = False
                defuse = DefUseAnalysis(func)
                mem = MemoryTracker(func)

                # Find unread allocas (zero loads)
                dead_allocas: Set[str] = set()
                for alloca_reg, loads in mem.alloca_loads.items():
                    if len(loads) == 0:
                        dead_allocas.add(alloca_reg)

                for block in func.blocks:
                    to_remove: List[IRInstruction] = []
                    for inst in block.instructions:
                        # Dead pure register
                        if inst.result and inst.is_pure() and defuse.is_dead(inst.result):
                            to_remove.append(inst)
                            changes += 1
                            func_changed = True
                            details.append(f"Eliminated unused computation: {inst.result} = {inst.opcode}")
                        # Dead store to an alloca with zero loads
                        elif inst.opcode == "store" and len(inst.operands) >= 2:
                            ptr_val = inst.operands[1].value
                            if ptr_val in dead_allocas:
                                to_remove.append(inst)
                                changes += 1
                                func_changed = True
                                details.append(f"Eliminated dead store to unread memory {ptr_val}")
                        # Dead alloca with zero loads and zero stores
                        elif inst.opcode == "alloca" and inst.result in dead_allocas:
                            if len(mem.alloca_stores.get(inst.result, [])) == 0:
                                to_remove.append(inst)
                                changes += 1
                                func_changed = True
                                details.append(f"Eliminated unused alloca {inst.result}")

                    for inst in to_remove:
                        block.remove_instruction(inst)

        return PassResult(
            pass_name=self.name,
            changes_made=changes,
            description=f"Eliminated {changes} dead instruction(s) and block(s)",
            details=details
        )
