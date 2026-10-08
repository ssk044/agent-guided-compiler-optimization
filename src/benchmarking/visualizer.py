"""
Matplotlib visualizer for benchmark results and performance comparisons.
"""
import os
from typing import Optional
import matplotlib
matplotlib.use("Agg") # Non-interactive headless backend
import matplotlib.pyplot as plt
from src.benchmarking.benchmark import BenchmarkResult


class BenchmarkVisualizer:
    @staticmethod
    def generate_chart(
        result: BenchmarkResult,
        title: str,
        output_image_path: str
    ) -> str:
        """
        Generates a 2-panel publication-grade comparison figure:
        Panel 1: Execution Time (ms) with standard deviation error bars.
        Panel 2: IR Instruction Count & Code Size Reduction.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_image_path)), exist_ok=True)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        fig.patch.set_facecolor('#0f172a') # Dark slate background

        # Panel 1: Execution Time
        categories = ["Baseline (-O0)", "LLM Optimized"]
        times = [result.baseline_mean_ms, result.optimized_mean_ms]
        errors = [result.baseline_std_ms, result.optimized_std_ms]
        colors = ["#ef4444", "#10b981"] # Red vs Green

        if result.clang_o1_mean_ms is not None:
            categories.append("Clang -O1")
            times.append(result.clang_o1_mean_ms)
            errors.append(0.0)
            colors.append("#3b82f6") # Blue

        if result.clang_o2_mean_ms is not None:
            categories.append("Clang -O2")
            times.append(result.clang_o2_mean_ms)
            errors.append(0.0)
            colors.append("#8b5cf6") # Purple

        ax1.set_facecolor('#1e293b')
        bars1 = ax1.bar(categories, times, yerr=errors, capsize=5, color=colors, edgecolor='#ffffff', alpha=0.9, width=0.55)
        ax1.set_ylabel("Execution Time (ms)", color='#f8fafc', fontsize=11, fontweight='bold')
        ax1.set_title(f"Runtime Performance ({result.speedup_percent:+.1f}% speedup)", color='#38bdf8', fontsize=12, fontweight='bold')
        ax1.tick_params(colors='#cbd5e1')
        ax1.grid(axis='y', linestyle='--', alpha=0.25, color='#ffffff')

        # Add text labels on top of bars
        for bar in bars1:
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2.0, height + 0.02 * max(times),
                f"{height:.3f} ms",
                ha='center', va='bottom', color='#f8fafc', fontsize=9, fontweight='bold'
            )

        # Panel 2: Instruction Count Reduction
        inst_categories = ["Baseline IR", "Optimized IR"]
        inst_counts = [result.baseline_instruction_count, result.optimized_instruction_count]
        inst_colors = ["#f59e0b", "#06b6d4"]

        ax2.set_facecolor('#1e293b')
        bars2 = ax2.bar(inst_categories, inst_counts, color=inst_colors, edgecolor='#ffffff', alpha=0.9, width=0.45)
        ax2.set_ylabel("LLVM IR Instructions", color='#f8fafc', fontsize=11, fontweight='bold')
        ax2.set_title(f"IR Instruction Count (-{result.instruction_reduction_percent:.1f}%)", color='#38bdf8', fontsize=12, fontweight='bold')
        ax2.tick_params(colors='#cbd5e1')
        ax2.grid(axis='y', linestyle='--', alpha=0.25, color='#ffffff')

        for bar in bars2:
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0, height + 0.02 * max(inst_counts if inst_counts[0] > 0 else [1]),
                f"{int(height)} ops",
                ha='center', va='bottom', color='#f8fafc', fontsize=10, fontweight='bold'
            )

        fig.suptitle(f"Compiler Optimization Analysis: {title}", color='#f8fafc', fontsize=14, fontweight='bold', y=0.98)
        plt.tight_layout()
        plt.savefig(output_image_path, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close(fig)

        return output_image_path
