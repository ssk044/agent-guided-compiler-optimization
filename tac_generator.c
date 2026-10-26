/*
 * ============================================================
 *  TAC (Three Address Code) Generator with JSON Output
 *  Compiler Optimization Project
 * ============================================================
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

/* ── Constants ─────────────────────────────────────────────── */
#define MAX_INSTR  100
#define MAX_LEN    32

/* ── TAC Instruction Structure ─────────────────────────────── */
typedef struct {
    char result[MAX_LEN];   /* destination temp variable      */
    char op[4];             /* operator:  + - * /  =          */
    char arg1[MAX_LEN];     /* left operand                   */
    char arg2[MAX_LEN];     /* right operand (empty for unary)*/
} Instruction;

/* ── TAC Program ───────────────────────────────────────────── */
typedef struct {
    Instruction code[MAX_INSTR];
    int         size;
    int         temp_count;
} TAC;

/* ── Helper: allocate a new temp name ─────────────────────── */
static void new_temp(TAC *t, char *buf) {
    sprintf(buf, "t%d", t->temp_count++);
}

/* ── Emit one instruction ──────────────────────────────────── */
static void emit(TAC *t,
                 const char *res,
                 const char *op,
                 const char *a1,
                 const char *a2)
{
    if (t->size >= MAX_INSTR) return;
    Instruction *ins = &t->code[t->size++];
    strncpy(ins->result, res, MAX_LEN - 1);
    strncpy(ins->op,     op,  3);
    strncpy(ins->arg1,   a1,  MAX_LEN - 1);
    strncpy(ins->arg2,   a2,  MAX_LEN - 1);
}

/* ── Lexer ─────────────────────────────────────────────────── */
typedef struct {
    const char *src;
    int         pos;
} Lexer;

static void skip_ws(Lexer *l) {
    while (l->src[l->pos] == ' ' || l->src[l->pos] == '\t')
        l->pos++;
}

/* forward declaration */
static void parse_expr(Lexer *l, TAC *t, char *out);

/* ── Parse primary: number | identifier | ( expr ) ─────────── */
static void parse_primary(Lexer *l, TAC *t, char *out) {
    skip_ws(l);
    if (l->src[l->pos] == '(') {
        l->pos++;                   /* eat '(' */
        parse_expr(l, t, out);
        skip_ws(l);
        if (l->src[l->pos] == ')') l->pos++;  /* eat ')' */
        return;
    }
    int start = l->pos;
    while (isalnum((unsigned char)l->src[l->pos]) || l->src[l->pos] == '_')
        l->pos++;
    int len = l->pos - start;
    if (len == 0) { strcpy(out, "?"); return; }
    strncpy(out, l->src + start, len);
    out[len] = '\0';
}

/* ── Parse term:  primary { (* | /) primary } ──────────────── */
static void parse_term(Lexer *l, TAC *t, char *out) {
    char left[MAX_LEN], right[MAX_LEN], tmp[MAX_LEN];
    parse_primary(l, t, left);
    skip_ws(l);
    while (l->src[l->pos] == '*' || l->src[l->pos] == '/') {
        char op[4] = { l->src[l->pos++], '\0' };
        parse_primary(l, t, right);
        new_temp(t, tmp);
        emit(t, tmp, op, left, right);
        strcpy(left, tmp);
        skip_ws(l);
    }
    strcpy(out, left);
}

/* ── Parse expr:  term { (+ | -) term } ────────────────────── */
static void parse_expr(Lexer *l, TAC *t, char *out) {
    char left[MAX_LEN], right[MAX_LEN], tmp[MAX_LEN];
    parse_term(l, t, left);
    skip_ws(l);
    while (l->src[l->pos] == '+' || l->src[l->pos] == '-') {
        char op[4] = { l->src[l->pos++], '\0' };
        parse_term(l, t, right);
        new_temp(t, tmp);
        emit(t, tmp, op, left, right);
        strcpy(left, tmp);
        skip_ws(l);
    }
    strcpy(out, left);
}

/* ── Evaluate integer expression for "possible outcome" ─────── */
static int eval_int(const char *expr) {
    /* tiny evaluator matching the same grammar */
    Lexer l = { expr, 0 };
    /* We'll reuse parse logic with a value stack approach */
    /* For simplicity: use a stack-based inline evaluator  */
    int  vals[32]; int vi = 0;
    char ops[32];  int oi = 0;

    int  prec(char c) { return (c == '*' || c == '/') ? 2 : 1; }
    void apply() {
        int b = vals[--vi], a = vals[--vi];
        char op = ops[--oi];
        if (op == '+') vals[vi++] = a + b;
        else if (op == '-') vals[vi++] = a - b;
        else if (op == '*') vals[vi++] = a * b;
        else if (op == '/' && b != 0) vals[vi++] = a / b;
        else vals[vi++] = 0;
    }

    while (expr[l.pos]) {
        skip_ws(&l);
        char c = expr[l.pos];
        if (isdigit((unsigned char)c)) {
            int num = 0;
            while (isdigit((unsigned char)expr[l.pos]))
                num = num * 10 + (expr[l.pos++] - '0');
            vals[vi++] = num;
        } else if (c == '(') {
            ops[oi++] = '('; l.pos++;
        } else if (c == ')') {
            while (oi > 0 && ops[oi-1] != '(') apply();
            if (oi > 0) oi--;          /* pop '(' */
            l.pos++;
        } else if (c == '+' || c == '-' || c == '*' || c == '/') {
            while (oi > 0 && ops[oi-1] != '(' && prec(ops[oi-1]) >= prec(c))
                apply();
            ops[oi++] = c; l.pos++;
        } else { l.pos++; }
    }
    while (oi > 0) apply();
    return vi > 0 ? vals[0] : 0;
}

/* ── Print JSON output ─────────────────────────────────────── */
static void print_json(int id,
                       const char *expr,
                       const char *num_expr,
                       int         outcome,
                       const TAC  *t)
{
    printf("  {\n");
    printf("    \"id\"                 : %d,\n",   id);
    printf("    \"expression\"         : \"%s\",\n", expr);
    printf("    \"numeric_form\"       : \"%s\",\n", num_expr);
    printf("    \"possible_outcome\"   : %d,\n",   outcome);
    printf("    \"tac_count\"          : %d,\n",   t->size);
    printf("    \"tac_instructions\"   : [\n");

    for (int i = 0; i < t->size; i++) {
        const Instruction *ins = &t->code[i];
        /* Format: result = arg1 op arg2 */
        if (strlen(ins->arg2) > 0)
            printf("      { \"step\": %d, \"instr\": \"%s = %s %s %s\" }",
                   i, ins->result, ins->arg1, ins->op, ins->arg2);
        else
            printf("      { \"step\": %d, \"instr\": \"%s = %s\" }",
                   i, ins->result, ins->arg1);

        printf("%s\n", i < t->size - 1 ? "," : "");
    }
    printf("    ]\n");
    printf("  }");
}

/* ── Main ──────────────────────────────────────────────────── */
int main(void) {

    /* Symbolic expressions → numeric equivalents */
    struct { const char *sym; const char *num; } tests[] = {
        { "a + b * c",          "2 + 3 * 4"         },
        { "(a + b) * c",        "(2 + 3) * 4"        },
        { "x * y + z * w",      "3 * 4 + 5 * 6"      },
        { "(p + q) * (r - s)",  "(10 + 2) * (8 - 3)" },
        { "a * b * c + d",      "2 * 3 * 4 + 5"      },
    };

    int n = (int)(sizeof tests / sizeof tests[0]);

    printf("[\n");
    for (int i = 0; i < n; i++) {
        TAC   tac  = { .size = 0, .temp_count = 0 };
        Lexer lex  = { tests[i].sym, 0 };
        char  final[MAX_LEN] = {0};

        /* Generate TAC */
        parse_expr(&lex, &tac, final);

        /* Final assignment: result_i = final_temp */
        char res[MAX_LEN];
        sprintf(res, "result%d", i + 1);
        emit(&tac, res, "=", final, "");

        /* Compute numeric outcome */
        int outcome = eval_int(tests[i].num);

        /* Print JSON block */
        print_json(i + 1, tests[i].sym, tests[i].num, outcome, &tac);
        printf("%s\n", i < n - 1 ? "," : "");
    }
    printf("]\n");

    return 0;
}
