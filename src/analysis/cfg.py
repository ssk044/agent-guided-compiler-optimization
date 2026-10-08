"""
Control-Flow Graph (CFG) representation and analysis for IR functions.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from src.llvm.ir_nodes import IRFunction, IRBasicBlock


@dataclass
class CFGNode:
    name: str
    block: IRBasicBlock
    predecessors: Set[str] = field(default_factory=set)
    successors: Set[str] = field(default_factory=set)

    @property
    def instruction_count(self) -> int:
        return len(self.block.instructions)


class ControlFlowGraph:
    def __init__(self, function: IRFunction):
        self.function = function
        self.nodes: Dict[str, CFGNode] = {}
        self.entry_node: Optional[CFGNode] = None
        self.exit_nodes: Set[str] = set()
        self._build_cfg()

    def _build_cfg(self):
        for block in self.function.blocks:
            node = CFGNode(
                name=block.name,
                block=block,
                predecessors=set(block.predecessors),
                successors=set(block.successors)
            )
            self.nodes[block.name] = node

        if self.function.blocks:
            self.entry_node = self.nodes[self.function.blocks[0].name]

        # Identify exit blocks (no successors or contains ret)
        for name, node in self.nodes.items():
            term = node.block.get_terminator()
            if not node.successors or (term and term.opcode == "ret"):
                self.exit_nodes.add(name)

    def get_reachable_blocks(self) -> Set[str]:
        """Performs BFS/DFS from entry node to find all reachable blocks."""
        if not self.entry_node:
            return set()
        visited = set()
        queue = [self.entry_node.name]
        while queue:
            cur = queue.pop(0)
            if cur not in visited:
                visited.add(cur)
                node = self.nodes.get(cur)
                if node:
                    for succ in node.successors:
                        if succ not in visited and succ in self.nodes:
                            queue.append(succ)
        return visited

    def get_unreachable_blocks(self) -> Set[str]:
        all_blocks = set(self.nodes.keys())
        reachable = self.get_reachable_blocks()
        return all_blocks - reachable

    def generate_ascii_graph(self) -> str:
        """Generates a text representation of the CFG with block statistics and edges."""
        lines = [f"CFG for @{self.function.name}:"]
        for name, node in self.nodes.items():
            preds_str = ", ".join(sorted(node.predecessors)) or "none"
            succs_str = ", ".join(sorted(node.successors)) or "exit"
            lines.append(f"  [{name}] ({node.instruction_count} instrs)")
            lines.append(f"    ├─ Preds: [{preds_str}]")
            lines.append(f"    └─ Succs: [{succs_str}]")
        return "\n".join(lines)

    def generate_mermaid(self) -> str:
        """Generates a Mermaid graph diagram for embedding in markdown reports."""
        lines = [f"```mermaid", f"graph TD", f"  %% CFG for @{self.function.name}"]
        for name, node in self.nodes.items():
            label = f"{name} ({node.instruction_count} ops)"
            lines.append(f'  {name}["{label}"]')
            for succ in node.successors:
                lines.append(f"  {name} --> {succ}")
        lines.append("```")
        return "\n".join(lines)
