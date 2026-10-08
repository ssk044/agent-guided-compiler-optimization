"""
Pydantic Schemas for LLM Agent Optimization Proposals.
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class OptimizationOpportunity(BaseModel):
    name: str = Field(description="Name of the optimization (e.g. ConstantFolding, StrengthReduction, DeadCodeElimination, LICM, CSE)")
    target_function: str = Field(description="Function where opportunity was identified, e.g. @compute")
    target_block: Optional[str] = Field(default=None, description="Basic block name if applicable, e.g. entry, for.body")
    target_instruction: Optional[str] = Field(default=None, description="Specific instruction or variable if applicable")
    rationale: str = Field(description="Detailed technical reasoning why this transformation is mathematically sound and safe")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")


class PassRecommendation(BaseModel):
    pass_name: str = Field(description="Name of the registered compiler pass to execute")
    order: int = Field(description="Execution sequence order (1, 2, 3...)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Pass configuration parameters")
    reason: str = Field(description="Why this pass should run at this stage of the pipeline")


class OptimizationProposal(BaseModel):
    summary: str = Field(description="Executive summary of the program analysis and optimization strategy")
    opportunities: List[OptimizationOpportunity] = Field(default_factory=list, description="List of fine-grained optimization opportunities found")
    recommended_passes: List[PassRecommendation] = Field(default_factory=list, description="Ordered pass pipeline recommended by the LLM agent")
    loop_optimizations: Optional[str] = Field(default=None, description="Specialized loop advice (unrolling, vectorization, invariant hoisting)")
    expected_speedup_estimate: float = Field(default=1.0, description="Estimated speedup multiplier (e.g. 1.15 for 15% speedup)")
    safety_assessment: str = Field(description="Verification reasoning confirming that semantic equivalence is strictly preserved")
