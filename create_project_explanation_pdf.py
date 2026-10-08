from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


OUTPUT = Path("output/pdf/compiler_agent_project_explanation.pdf")


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.line(doc.leftMargin, 0.52 * inch, A4[0] - doc.rightMargin, 0.52 * inch)
    canvas.setFillColor(colors.HexColor("#475569"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(doc.leftMargin, 0.34 * inch, "Automated LLM/Agent-Guided Compiler Code Optimization")
    canvas.drawRightString(A4[0] - doc.rightMargin, 0.34 * inch, f"Page {doc.page}")
    canvas.restoreState()


def p(text, style):
    return Paragraph(text, style)


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=0.62 * inch, leftMargin=0.62 * inch,
        topMargin=0.55 * inch, bottomMargin=0.72 * inch,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=17,
                           leading=21, alignment=TA_CENTER, textColor=colors.HexColor("#0F172A"), spaceAfter=7)
    subtitle = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=9.5, leading=12,
                              alignment=TA_CENTER, textColor=colors.HexColor("#475569"), spaceAfter=14)
    h = ParagraphStyle("Heading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11,
                       leading=14, textColor=colors.HexColor("#0F4C81"), spaceBefore=7, spaceAfter=3)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2,
                          leading=12.2, textColor=colors.HexColor("#1F2937"), spaceAfter=5)
    small = ParagraphStyle("Small", parent=body, fontSize=8.4, leading=10.5)
    code = ParagraphStyle("Code", parent=body, fontName="Courier", fontSize=8.2, leading=10.2,
                          leftIndent=9, rightIndent=9, textColor=colors.HexColor("#1E3A5F"))

    story = [
        p("Automated LLM/Agent-Guided Compiler Code Optimization", title),
        p("Two-page technical explanation for project demonstration and viva", subtitle),
        p("What the project does", h),
        p("This project is a compiler-design system that accepts a C program, converts it into intermediate code, "
          "finds safe optimization opportunities, verifies every proposed change, and accepts a change only when the "
          "program still behaves identically and its measured weighted cost becomes lower. It combines classical compiler "
          "optimization with an optional local language-model assistant. The language model can suggest a safe pass order, "
          "but it never has authority to commit code changes.", body),
        p("End-to-end pipeline", h),
        p("C source -&gt; lexical analysis -&gt; parsing and AST -&gt; symbol table and semantic analysis -&gt; "
          "intermediate code -&gt; analysis -&gt; optimization -&gt; verification -&gt; cost evaluation -&gt; final output.", code),
        p("The project already contains a lexer, recursive-descent parser, AST nodes, symbol-table support, and semantic "
          "checks. The executable intermediate representation is LLVM IR. A separate TAC-style display is generated for "
          "academic clarity: TAC presents operations in simple forms such as <i>t1 = a + b</i>, while LLVM IR additionally "
          "models types, basic blocks, memory operations, branches, loops, and calls.", body),
        p("Core agent components", h),
    ]
    rows = [
        [p("Component", small), p("Responsibility", small)],
        [p("Orchestrator", small), p("Runs analyze -&gt; propose -&gt; verify -&gt; evaluate -&gt; accept/reject until no beneficial opportunity remains.", small)],
        [p("Code Analysis Specialist", small), p("Finds constant pairs, algebraic patterns, dead results, repeated subexpressions, arithmetic operations, basic blocks, and loop information.", small)],
        [p("Optimization Specialist", small), p("Uses compiler passes in rule mode, or uses optional local LLM guidance to prioritize available safe passes.", small)],
        [p("Verification Module", small), p("Compiles baseline and candidate programs and performs differential testing on 13 inputs.", small)],
        [p("Cost Evaluator", small), p("Compares a weighted score based on instructions, expensive arithmetic, temporary values, and measured runtime.", small)],
    ]
    table = Table(rows, colWidths=[1.6 * inch, 5.35 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [table, Spacer(1, 5), p("How a candidate is accepted", h),
              p("For each optimization pass, the orchestrator creates a copy of the current LLVM IR. It never modifies the accepted version directly. "
                "The candidate copy is compiled. If compilation fails, it is rejected. If it compiles, the baseline and candidate executables are run using one default case, edge cases, and reproducible random inputs. "
                "The verifier compares standard output, exit codes, and timeouts. Any mismatch causes rejection.", body),
              p("Weighted cost = instruction count + 3 x expensive arithmetic operations + temporary register count + 10 x mean execution time in milliseconds.", code),
              p("Therefore, the acceptance rule is: <b>accept only if output verification passes AND candidate cost is lower.</b> "
                "This fail-closed design ensures that an incorrect or unhelpful transformation is not committed.", body),
              PageBreak(),
              p("Optimization Methods and Syllabus Connection", h),
              p("The project demonstrates standard code-optimization concepts from compiler design. Constant propagation replaces known variables with their values. "
                "Constant folding evaluates expressions such as <i>10 + 20</i> during compilation. Strength reduction replaces costly arithmetic, for example <i>x * 8</i> with a left shift. "
                "Common-subexpression elimination avoids repeated calculations. Dead-code elimination removes values that do not affect output. Loop-invariant code motion can move calculations outside loops when their values do not change per iteration.", body),
              p("For code-generation topics, the final LLVM IR can be lowered into a short target-assembly excerpt. For intermediate-code topics, the program can show TAC-style views before and after optimization. "
                "This connects the project to lexical analysis, parsing, symbol tables, semantic analysis, intermediate-code generation, basic blocks, control flow, data-flow analysis, loop optimization, machine-independent optimization, and target-code generation.", body),
              p("Example", h),
              p("A program may contain: <i>int a = 10 + 20;</i>, <i>int unused = 5 * 4;</i>, and repeated calculations such as <i>4 * 8</i>. "
                "The compiler can fold constants to 30 and 32, remove the unused assignment, and simplify intermediate operations. The original and optimized programs must still print the same value, for example <i>Result: 94</i>.", body),
              p("Interactive Demonstration", h),
              p("When the main program runs, the user can choose to paste C code, run a small dataset demo, or run the full dataset. "
                "For pasted code, the program optionally asks whether to use local LLM guidance and whether to display educational TAC and assembly views. "
                "The concise terminal result shows accepted or rejected transformations, original output, optimized output, number of matching tests, final PASS or FAIL status, cost reduction, and an optimized IR excerpt.", body),
              p("Dataset, Metrics, and Reports", h),
              p("The project automatically generates 500 benchmark programs: arithmetic-only, nested expressions, repeated expressions, dead code, loops, conditionals, and mixed programs. "
                "For every program it records the decision history, final cost, final IR, output-match verdict, and convergence steps. Aggregate reports include verification pass rate, acceptance rate, average cost reduction, convergence distribution, LLM validity rate when enabled, and false-positive rate. "
                "Generated charts include a decision-flow Sankey diagram, per-optimization bar chart, iteration-cost line chart, optimization pie chart, steps-versus-improvement scatter plot, and category heatmap.", body),
              p("Key Viva Statement", h),
              p("This is a compiler-design project enhanced with an optional intelligent assistant. The core logic remains compiler based: intermediate-code analysis, data-flow and loop analysis, classical optimization passes, differential testing, cost measurement, and safe code generation. "
                "The LLM is only an advisor; correctness and cost evaluation decide every final optimization.", body)]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build()
