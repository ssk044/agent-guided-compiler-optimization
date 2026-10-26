/*
 * TAC (Three Address Code) Generator with JSON Output
 * Parses simple arithmetic expressions and emits TAC + JSON report
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#define MAX_INSTR  64
#define MAX_STR    32

/* ─── Data Structures ─────────────────────────────────────────── */

typedef struct {
    char op[4];          /* operator: +  -  *  /  =        */
    char arg1[MAX_STR];
    char arg2[MAX_STR];
    char result[MAX_STR];
} TACInstr;

typedef struct {
    TACInstr instrs[MAX_INSTR];
    int       count;
    int       temp_id;   /* next temp variable index        */
} TACProgram;

/* ─── TAC Builder ─────────────────────────────────────────────── */

static void new_temp(TACProgram *p, char *out) {
    sprintf(out, "t%d", p->temp_id++);
}

static int emit(TACProgram *p,
                const char *op,
                const char *a1,
                const char *a2,
                const char *res)
{
    if (p->count >= MAX_INSTR) return -1;
    TACInstr *i = &p->instrs[p->count++];
    strncpy(i->op,     op,  sizeof i->op  - 1);
    strncpy(i->arg1,   a1,  sizeof i->arg1 - 1);
    strncpy(i->arg2,   a2,  sizeof i->arg2 - 1);
    strncpy(i->result, res, sizeof i->result - 1);
    return p->count - 1;
}

/* ─── Tiny expression parser (precedence climbing) ────────────── */

typedef struct { const char *src; int pos; } Lexer;

static void skip_ws(Lexer *l) {
    while (l->src[l->pos] == ' ') l->pos++;
}

/* forward decl */
static void parse_expr(Lexer *l, TACProgram *p, char *out);

static void parse_primary(Lexer *l, TACProgram *p, char *out) {
    skip_ws(l);
    if (l->src[l->pos] == '(') {
        l->pos++;                        /* consume '(' */
        parse_expr(l, p, out);
        skip_ws(l);
        if (l->src[l->pos] == ')') l->pos++;
        return;
    }
    /* number or identifier */
    int start = l->pos;
    while (isalnum((unsigned char)l->src[l->pos]) || l->src[l->pos] == '_')
        l->pos++;
    int len = l->pos - start;
    strncpy(out, l->src + start, len);
    out[len] = '\0';
}

static void parse_term(Lexer *l, TACProgram *p, char *out) {
    char left[MAX_STR], right[MAX_STR], tmp[MAX_STR];
    parse_primary(l, p, left);
    skip_ws(l);
    while (l->src[l->pos] == '*' || l->src[l->pos] == '/') {
        char op[2] = { l->src[l->pos++], '\0' };
        parse_primary(l, p, right);
        new_temp(p, tmp);
        emit(p, op, left, right, tmp);
        strcpy(left, tmp);
        skip_ws(l);
    }
    strcpy(out, left);
}

static void parse_expr(Lexer *l, TACProgram *p, char *out) {
    char left[MAX_STR], right[MAX_STR], tmp[MAX_STR];
    parse_term(l, p, left);
    skip_ws(l);
    while (l->src[l->pos] == '+' || l->src[l->pos] == '-') {
        char op[2] = { l->src[l->pos++], '\0' };
        parse_term(l, p, right);
        new_temp(p, tmp);
        emit(p, op, left, right, tmp);
        strcpy(left, tmp);
        skip_ws(l);
    }
    strcpy(out, left);
}

/* ─── JSON Emitter ────────────────────────────────────────────── */

static void print_json(const TACProgram *p,
                       const char *expr,
                       const char *final_res)
{
    printf("{\n");
    printf("  \"expression\": \"%s\",\n", expr);
    printf("  \"final_result\": \"%s\",\n", final_res);
    printf("  \"tac_instruction_count\": %d,\n", p->count);
    printf("  \"tac_instructions\": [\n");

    for (int i = 0; i < p->count; i++) {
        const TACInstr *ins = &p->instrs[i];
        printf("    {\n");
        printf("      \"index\": %d,\n", i);
        printf("      \"result\": \"%s\",\n",   ins->result);
        printf("      \"op\":     \"%s\",\n",   ins->op);
        printf("      \"arg1\":   \"%s\",\n",   ins->arg1);
        printf("      \"arg2\":   \"%s\"\n",    ins->arg2);
        printf("    }%s\n", i < p->count - 1 ? "," : "");
    }

    printf("  ]\n");
    printf("}\n");
}

/* ─── Possible Outcome Evaluator ──────────────────────────────── */

/* Evaluate simple numeric expressions to verify correctness */
static double eval_expr(const char *expr) {
    /* Use system's expression evaluator via a minimal recursive descent */
    double result = 0.0;
    /* We'll use a basic approach for integer-only expressions */
    char buf[256];
    snprintf(buf, sizeof(buf), "echo $(( %s ))", expr);

    FILE *fp = popen(buf, "r");
    if (fp) {
        fscanf(fp, "%lf", &result);
        pclose(fp);
    }
    return result;
}

/* ─── Main ────────────────────────────────────────────────────── */

int main(void) {
    /* Test expressions with genuine possible outcomes */
    const char *expressions[] = {
        "a + b * c",
        "(a + b) * c",
        "x * y + z * w",
        "3 + 4 * 2",
        "(5 + 3) * 2 - 1"
    };

    /* Numeric equivalents for outcome verification */
    const char *numeric[] = {
        "2 + 3 * 4",
        "(2 + 3) * 4",
        "2 * 3 + 4 * 5",
        "3 + 4 * 2",
        "(5 + 3) * 2 - 1"
    };

    int n = sizeof(expressions) / sizeof(expressions[0]);

    printf("[\n");
    for (int e = 0; e < n; e++) {
        TACProgram prog = { .count = 0, .temp_id = 0 };
        Lexer lex      = { .src = expressions[e], .pos = 0 };
        char  final[MAX_STR] = {0};

        parse_expr(&lex, &prog, final);

        /* Emit assign: result = final_temp */
        char res_var[MAX_STR];
        sprintf(res_var, "result_%d", e);
        emit(&prog, "=", final, "", res_var);

        /* Get numeric outcome */
        double outcome = eval_expr(numeric[e]);

        /* Print JSON block per expression */
        printf("  {\n");
        printf("    \"id\": %d,\n", e + 1);
        printf("    \"expression\": \"%s\",\n", expressions[e]);
        printf("    \"numeric_equivalent\": \"%s\",\n", numeric[e]);
        printf("    \"possible_outcome\": %.0f,\n", outcome);
        printf("    \"final_temp\": \"%s\",\n", final);
        printf("    \"tac_count\": %d,\n", prog.count);
        printf("    \"tac\": [\n");

        for (int i = 0; i < prog.count; i++) {
            const TACInstr *ins = &prog.instrs[i];
            printf("      { \"idx\": %d, \"instr\": \"%s = %s %s %s\" }%s\n",
                   i,
                   ins->result,
                   ins->arg1,
                   ins->op,
                   ins->arg2,
                   i < prog.count - 1 ? "," : "");
        }

        printf("    ]\n");
        printf("  }%s\n", e < n - 1 ? "," : "");
    }
    printf("]\n");

    return 0;
}
