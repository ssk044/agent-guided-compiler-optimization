"""
Dominator tree and Dominance Frontier analysis for Control-Flow Graphs.
"""
from typing import Dict, Set, Optional
from src.analysis.cfg import ControlFlowGraph


class DominatorAnalysis:
    def __init__(self, cfg: ControlFlowGraph):
        self.cfg = cfg
        self.dom: Dict[str, Set[str]] = {} # Node -> Set of dominators
        self.idom: Dict[str, Optional[str]] = {} # Node -> Immediate dominator
        self.dom_tree_children: Dict[str, Set[str]] = {} # Node -> Dominator tree children
        self.dom_frontier: Dict[str, Set[str]] = {} # Node -> Dominance Frontier
        self._compute_dominators()
        self._compute_idoms()
        self._compute_dominance_frontiers()

    def _compute_dominators(self):
        nodes = list(self.cfg.nodes.keys())
        if not nodes or not self.cfg.entry_node:
            return

        entry = self.cfg.entry_node.name
        all_nodes = set(nodes)

        # Initialization
        self.dom[entry] = {entry}
        for n in nodes:
            if n != entry:
                self.dom[n] = set(all_nodes)

        # Iterative fixed-point algorithm
        changed = True
        while changed:
            changed = False
            for n in nodes:
                if n == entry:
                    continue
                node = self.cfg.nodes[n]
                preds = [p for p in node.predecessors if p in self.dom]
                if not preds:
                    new_dom = {n}
                else:
                    intersection = set(self.dom[preds[0]])
                    for p in preds[1:]:
                        intersection &= self.dom[p]
                    new_dom = {n} | intersection

                if new_dom != self.dom[n]:
                    self.dom[n] = new_dom
                    changed = True

    def _compute_idoms(self):
        entry = self.cfg.entry_node.name if self.cfg.entry_node else None
        for n in self.cfg.nodes:
            self.dom_tree_children[n] = set()
            self.idom[n] = None

        for n, doms in self.dom.items():
            if n == entry:
                continue
            # Strict dominators
            sdoms = doms - {n}
            # idom is the sdom that dominates no other sdom of n
            for candidate in sdoms:
                other_sdoms = sdoms - {candidate}
                if all(candidate not in self.dom.get(other, set()) for other in other_sdoms):
                    self.idom[n] = candidate
                    self.dom_tree_children[candidate].add(n)
                    break

    def _compute_dominance_frontiers(self):
        for n in self.cfg.nodes:
            self.dom_frontier[n] = set()

        for b_name, b_node in self.cfg.nodes.items():
            if len(b_node.predecessors) >= 2:
                for p in b_node.predecessors:
                    runner = p
                    while runner and runner != self.idom.get(b_name):
                        self.dom_frontier[runner].add(b_name)
                        runner = self.idom.get(runner)

    def dominates(self, a: str, b: str) -> bool:
        """Returns True if block 'a' dominates block 'b'."""
        return a in self.dom.get(b, set())

    def strictly_dominates(self, a: str, b: str) -> bool:
        return a != b and self.dominates(a, b)
