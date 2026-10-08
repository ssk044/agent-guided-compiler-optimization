"""
Constant Propagation Optimization Pass.
Propagates known constant values across registers and single-store memory locations.
"""
import re
from typing import Dict, Optional, Set
from src.optimizations.base import OptimizationPass, PassResult
from src.llvm.ir_nodes import IRModule, IRFunction, IRInstruction
from src.analysis.dataflow import MemoryTracker


class ConstantPropagationPass(OptimizationPass):
    def __init__(self):
        super().__init__("ConstantPropagation")

    def run(self, module: IRModule) -> PassResult:
        changes = 0
        details = []

        for func in module.functions:
            if func.is_declaration:
                continue

            # Track alloca slots that have exactly one store of a constant
            mem_tracker = MemoryTracker(func)
            const_allocas: Dict[str, str] = {} # alloca_reg -> const_val

            for alloca_reg, stores in mem_tracker.alloca_stores.items():
                if len(stores) == 1:
                    store_inst = stores[0]
                    val_op = store_inst.operands[0]
                    if val_op.is_constant():
                        const_allocas[alloca_reg] = val_op.value

            # Propagate constants to loads
            for block in func.blocks:
                to_remove = []
                for inst in block.instructions:
                    if inst.opcode == "load" and inst.operands:
                        ptr_var = inst.operands[0].value
                        if ptr_var in const_allocas and inst.result:
                            const_val = const_allocas[ptr_var]
                            load_res = inst.result
                            changes += 1
                            details.append(f"Propagated constant {const_val} from {ptr_var} to {load_res}")
                            self._substitute_everywhere(func, load_res, const_val)
                            to_remove.append(inst)

                for inst in to_remove:
                    block.remove_instruction(inst)

        return PassResult(
            pass_name=self.name,
            changes_made=changes,
            description=f"Propagated {changes} constant value(s)",
            details=details
        )

    def _substitute_everywhere(self, func: IRFunction, old_reg: str, new_val: str):
        for block in func.blocks:
            for inst in block.instructions:
                inst.replace_variable_use(old_reg, new_val)
