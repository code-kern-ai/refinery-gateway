from typing import Optional
from sqlglot import parse_one, tokenize
from sqlglot.errors import ParseError
from sqlglot import expressions as exp

from sqlglot import TokenType

from sqlalchemy.sql import text as sql_text

# relative import so it works in console and in module
from .constants import (
    ALLOWED_NODES,
    ALLOWED_TOKEN_TYPES,
    ALLOWED_COLUMN_PREFIX,
    DISALLOWED_COLUMN_PREFIX,
)


def parse_sql_text(sql: str) -> str:
    return sql_text(sql)


def validate_sql_clause(
    select: Optional[str] = None,
    where: Optional[str] = None,
    order_by: Optional[str] = None,
    include_db_check: bool = False,
) -> str | None:
    """
    Validate a user-provided WHERE clause.
    Returns None if safe, otherwise a string reason for rejection.
    """
    if not where and not order_by and not select:
        return "No SELECT, WHERE or ORDER BY clause provided"
    select_or_where_or_order_by = select or where or order_by
    what = "WHERE" if where else "ORDER BY" if order_by else "SELECT"
    # Step 1: reject unsafe tokens
    if reason := __contains_disallowed_tokens(select_or_where_or_order_by):
        return reason

    # Step 2: parse the WHERE clause as an expression
    try:
        expr = parse_one(select_or_where_or_order_by, read="postgres")
    except ParseError:
        return f"Parse error => invalid {what} condition, check for correct syntax"

    if reason := __contains_always_true(expr):
        return reason

    # Step 3: walk AST nodes
    for node in expr.walk():
        if node.key not in ALLOWED_NODES:
            return f"Disallowed node: {node.key}"

        if node.key == "column":
            if not str(node).startswith(ALLOWED_COLUMN_PREFIX):
                return f"Column does not start with allowed prefix: {str(node)}"
    if include_db_check:
        # import here to avoid test file dependency issues
        from submodules.model.business_objects import general

        try:
            if select:
                general.execute_all(
                    "SELECT " + select + " FROM public.record r LIMIT 0"
                )
            elif where:
                general.execute_all(
                    "SELECT 1 FROM public.record r WHERE " + where + " LIMIT 0"
                )
            elif order_by:
                general.execute_all(
                    "SELECT 1 FROM public.record r ORDER BY " + order_by + " LIMIT 0"
                )
        except Exception as e:
            general.rollback()
            return f"Database error when validating {what} clause: {e}"
    return None


def __contains_disallowed_tokens(sql: str) -> str | None:
    """
    Check for comments or dangerous system functions.
    Returns a string reason if disallowed, None otherwise.
    """
    try:
        for t in tokenize(sql):
            if t.token_type not in ALLOWED_TOKEN_TYPES:
                return f"Disallowed token type: {t.text}"
            if (
                t.token_type == TokenType.IDENTIFIER or t.token_type == TokenType.VAR
            ) and t.text.lower().startswith(DISALLOWED_COLUMN_PREFIX):
                return f"Disallowed system function: {t.text}"
            if t.comments:
                return "Comments are not allowed"
    except Exception as e:
        return f"Tokenization error - invalid WHERE condition: {str(e)}"
    return None


def __contains_always_true(expr):
    """
    Return a string reason if expr is provably always-true, otherwise None.

    Rules covered:
     - A top-level Boolean literal TRUE (exp.Boolean) -> always-true
     - A CAST to BOOLEAN whose inner is a literal 1/TRUE -> always-true
       (but NOT a cast of a column/expression)
     - EQ of two identical literals (1 = 1, 'a' = 'a') -> always-true
     - OR: if any branch is always-true -> always-true
     - AND: if both branches are always-true -> always-true
     - Parentheses are unwrapped
    """
    # Unwrap parentheses
    if isinstance(expr, exp.Paren):
        inner = expr.args.get("this")
        if isinstance(inner, exp.Expression):
            return __contains_always_true(inner)

    # EQ: literal = literal (both sides must be literals and equal)
    if isinstance(expr, exp.EQ):
        left = expr.args.get("this")
        right = expr.args.get("expression")
        if isinstance(left, exp.Literal) and isinstance(right, exp.Literal):
            # For safety compare their `.this` representation; adapt if you need type-aware compare
            if left.this == right.this:
                return f"Always-true expression: {left.this} = {right.this}"
        # Do NOT recurse into left/right here — a literal RHS TRUE does not make the EQ always true.

    # Cast to BOOLEAN of a literal (like 1::BOOLEAN)
    if isinstance(expr, exp.Cast):
        to_type = expr.args.get("to")
        inner = expr.args.get("this")
        # to_type could be an Identifier, DataType, or other node; string compare is pragmatic
        if to_type and isinstance(inner, exp.Literal):
            try:
                typ = str(to_type).upper()
            except Exception:
                typ = ""
            if "BOOLEAN" in typ:
                # Treat literal 1 / '1' / True / 'TRUE' as always-true (adapt to your dialect needs)
                if inner.this in (1, "1", True, "TRUE"):
                    return f"Always-true cast: {inner.this}::BOOLEAN"
        # Do NOT treat casts of non-literals as always-true.

    # Top-level Boolean literal: only flag if expr itself is the Boolean node
    if isinstance(expr, exp.Boolean):
        if expr.this:  # True value
            return f"Always-true boolean literal: {expr.this}"
        # If it's FALSE, it's not always-true; ignore.

    # OR: any branch always-true => whole expression always-true
    if isinstance(expr, exp.Or):
        left = expr.args.get("this")
        right = expr.args.get("expression")
        if left and isinstance(left, exp.Expression):
            if reason := __contains_always_true(left):
                return reason
        if right and isinstance(right, exp.Expression):
            if reason := __contains_always_true(right):
                return reason

    # AND: both branches must be always-true
    if isinstance(expr, exp.And):
        left = expr.args.get("this")
        right = expr.args.get("expression")
        left_reason = (
            __contains_always_true(left) if isinstance(left, exp.Expression) else None
        )
        right_reason = (
            __contains_always_true(right) if isinstance(right, exp.Expression) else None
        )
        if left_reason and right_reason:
            return f"Always-true AND expression: {left_reason} and {right_reason}"

    # For all other node types, do NOT descend into arbitrary children:
    # only recurse into child expressions that are meaningful for short-circuit logic.
    # This prevents a Boolean literal nested as part of a larger expression from being treated as the whole expression.
    return None
