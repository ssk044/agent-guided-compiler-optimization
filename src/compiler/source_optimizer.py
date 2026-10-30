"""Conservative source rewrites; this is not an LLVM-to-C decompiler."""
import json
from pathlib import Path
import re
import subprocess
import tempfile


def optimize_c_source(source: str) -> dict:
    """Rewrite unused literal printf calls only; leave unsupported code intact.

    Clang's AST identifies real calls used as standalone statements. Formats,
    macros, consumed return values and source-defined/shadowed library names are
    excluded. No submitted program is executed.
    """
    unchanged = dict(optimized_source=source, source_optimization_count=0,
                     source_optimization_note='No supported safe source rewrites found; C source is unchanged. '
                     'LLVM IR and assembly can still contain compiler optimizations.')
    with tempfile.TemporaryDirectory(prefix='source_optimizer_') as directory:
        path = Path(directory) / 'program.c'
        path.write_text(source, encoding='utf-8')
        process = subprocess.run(['clang', '-Xclang', '-ast-dump=json', '-fsyntax-only', str(path)],
                                 capture_output=True, text=True)
        if process.returncode:
            return unchanged
        tree = json.loads(process.stdout)
        edits = []
        blocked = False
        raw = source.encode('utf-8')

        def visit(node, parent=None):
            nonlocal blocked
            location = node.get('loc', {})
            # Source declarations that could override printf/fputs/stdout.
            if (node.get('kind') in ('FunctionDecl', 'VarDecl', 'ParmVarDecl')
                    and node.get('name') in ('printf', 'fputs', 'stdout')
                    and 'offset' in location and not location.get('includedFrom')):
                blocked = True
            if node.get('kind') == 'CallExpr' and parent and parent.get('kind') == 'CompoundStmt':
                bounds = node.get('range', {})
                start, end = bounds.get('begin', {}), bounds.get('end', {})
                if 'offset' in start and 'offset' in end and not start.get('includedFrom'):
                    a, b = start['offset'], end['offset'] + end.get('tokLen', 1)
                    call = raw[a:b].decode('utf-8')
                    match = re.fullmatch(r'printf\s*\(\s*("(?:[^"\\]|\\.)*")\s*\)', call, re.S)
                    # Exclude escaped percent encodings as well as visible formats.
                    if match and '%' not in match[1] and '\\' not in match[1]:
                        edits.append((a, b, f'fputs({match[1]}, stdout)'.encode('utf-8')))
            for child in node.get('inner', []):
                visit(child, node)

        visit(tree)
        # Macros can change the meaning of library names at the replacement site.
        if blocked or re.search(r'^\s*#\s*(?:define|undef)\b', source, re.M):
            return unchanged
        for a, b, replacement in sorted(edits, reverse=True):
            raw = raw[:a] + replacement + raw[b:]
        if not edits:
            return unchanged
        candidate = raw.decode('utf-8')
        path.write_text(candidate, encoding='utf-8')
        check = subprocess.run(['clang', '-fsyntax-only', str(path)], capture_output=True, text=True)
        if check.returncode:
            return unchanged
        return dict(optimized_source=candidate, source_optimization_count=len(edits),
                    source_optimization_note=f'{len(edits)} unused literal printf call(s) rewritten to fputs. '
                    'This conservative C source view is separate from LLVM optimization; it is not decompiled LLVM IR.')
