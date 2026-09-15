from ast_nodes import Const, Var, Assign, Print, BinOp, RelOp, Cast, Ternary
from SymbolTable import DataType
from type_rules import is_numeric, promote, SemanticError


class TypeChecker:

    def __init__(self, symbol_table):
        self.symbol_table = symbol_table
        self.errors = []

    def error(self, message, lineno):
        self.errors.append(SemanticError(message, lineno))

    # Main expression checker
    def check_expr(self, node):

        if isinstance(node, Const):
            return node, node.type

        elif isinstance(node, Var):
            return self.check_var(node)

        elif isinstance(node, BinOp):
            return self.check_binop(node)

        elif isinstance(node, RelOp):
            return self.check_relop(node)

        elif isinstance(node, Cast):
            return self.check_cast(node)

        elif isinstance(node, Ternary):
            return self.check_ternary(node)

        return node, DataType.INT


    # 1. Variable checking
    def check_var(self, node):

        entry = self.symbol_table.getSymbol(node.name)

        if entry is None:
            self.error(
                f"undeclared variable '{node.name}'",
                node.lineno
            )
            return node, DataType.INT

        return node, entry.getDataType()


    # 2. Arithmetic expressions
    def check_binop(self, node):

        left, left_type = self.check_expr(node.left)
        right, right_type = self.check_expr(node.right)

        if not is_numeric(left_type) or not is_numeric(right_type):
            self.error(
                f"arithmetic operator '{node.op}' requires numeric operands",
                node.lineno
            )
            return node, DataType.INT

        result_type = promote(left_type, right_type)

        if left_type != result_type:
            left = Cast(result_type, left, node.lineno)

        if right_type != result_type:
            right = Cast(result_type, right, node.lineno)

        return BinOp(node.op, left, right, node.lineno), result_type


    # 3. Relational expressions
    def check_relop(self, node):

        left, left_type = self.check_expr(node.left)
        right, right_type = self.check_expr(node.right)

        # Numeric comparisons
        if is_numeric(left_type) and is_numeric(right_type):

            common_type = promote(left_type, right_type)

            if left_type != common_type:
                left = Cast(common_type, left, node.lineno)

            if right_type != common_type:
                right = Cast(common_type, right, node.lineno)

            return RelOp(node.op, left, right, node.lineno), DataType.INT

        # String equality only
        if left_type == DataType.STRING and right_type == DataType.STRING:
            if node.op in ("==", "!="):
                return RelOp(node.op, left, right, node.lineno), DataType.INT

        self.error(
            f"incompatible operands for '{node.op}'",
            node.lineno
        )

        return node, DataType.INT


    # 4. Explicit casts
    def check_cast(self, node):

        expr, expr_type = self.check_expr(node.expr)
        target_type = node.target_type

        if expr_type == target_type:
            return Cast(target_type, expr, node.lineno), target_type

        if is_numeric(expr_type) and is_numeric(target_type):
            return Cast(target_type, expr, node.lineno), target_type

        self.error(
            f"invalid cast from {expr_type} to {target_type}",
            node.lineno
        )

        return node, target_type


    # 5. Ternary expressions
    def check_ternary(self, node):

        cond, cond_type = self.check_expr(node.cond)
        then_expr, then_type = self.check_expr(node.then_expr)
        else_expr, else_type = self.check_expr(node.else_expr)

        if not is_numeric(cond_type):
            self.error(
                "ternary condition must be numeric",
                node.lineno
            )

        if then_type == else_type:
            return Ternary(cond, then_expr, else_expr, node.lineno), then_type

        if is_numeric(then_type) and is_numeric(else_type):

            result_type = promote(then_type, else_type)

            if then_type != result_type:
                then_expr = Cast(result_type, then_expr, node.lineno)

            if else_type != result_type:
                else_expr = Cast(result_type, else_expr, node.lineno)

            return Ternary(
                cond, then_expr, else_expr, node.lineno
            ), result_type

        self.error(
            "incompatible ternary branch types",
            node.lineno
        )

        return node, then_type


    # 6. Assignment statements
    def check_assign_stmt(self, node):

        var, var_type = self.check_var(node.var)
        expr, expr_type = self.check_expr(node.expr)

        if var_type == expr_type:
            return Assign(var, expr, node.lineno)

        # Numeric conversions allowed
        if is_numeric(var_type) and is_numeric(expr_type):
            expr = Cast(var_type, expr, node.lineno)
            return Assign(var, expr, node.lineno)

        self.error(
            f"cannot assign {expr_type} to {var_type}",
            node.lineno
        )

        return Assign(var, expr, node.lineno)


    # Check statements
    def check_statement(self, node):

        if isinstance(node, Assign):
            return self.check_assign_stmt(node)

        elif isinstance(node, Print):
            expr, _ = self.check_expr(node.expr)
            return Print(expr, node.lineno)

        return node


    # Check complete function
    def check_function(self, function):

        new_statements = []

        for stmt in function.getStatementsAstList():
            new_statements.append(self.check_statement(stmt))

        function.setStatementsAstList(new_statements)

        return self.errors


# Program-level function called by main.py
def check_program(program):

    all_errors = []

    for function in program.getFunctions():

        checker = TypeChecker(function.getLocalSymbolTable())

        errors = checker.check_function(function)

        all_errors.extend(errors)

    return all_errors
