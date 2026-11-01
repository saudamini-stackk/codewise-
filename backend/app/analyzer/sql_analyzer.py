import re
from typing import Optional, List, Dict, Any
from ..models import (
    AnalysisResult,
    LineExplanation,
    VariableFunctionItem,
    DiagnosticItem,
    ComplexityInfo
)
from .base import BaseAnalyzer, extract_lines

# Import sqlparse with fallback
try:
    import sqlparse
    from sqlparse.sql import IdentifierList, Identifier, Where
    from sqlparse.tokens import Keyword, DML
    SQLPARSE_AVAILABLE = True
except ImportError:
    SQLPARSE_AVAILABLE = False

class SqlAnalyzer(BaseAnalyzer):
    """
    Specialized analyzer for SQL queries and DDL statements.
    Explains queries, joins, filtering, aggregations, relational logic, and potential performance/safety issues.
    """

    def analyze(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []
        clean_sql = code.strip()
        upper_sql = clean_sql.upper()

        # 1. Detect query command type
        command_type = "Query"
        if upper_sql.startswith("SELECT"):
            command_type = "SELECT (Data Retrieval)"
        elif upper_sql.startswith("INSERT"):
            command_type = "INSERT (Data Insertion)"
        elif upper_sql.startswith("UPDATE"):
            command_type = "UPDATE (Data Mutation)"
        elif upper_sql.startswith("DELETE"):
            command_type = "DELETE (Row Deletion)"
        elif upper_sql.startswith("CREATE TABLE"):
            command_type = "CREATE TABLE (DDL Schema Definition)"
        elif upper_sql.startswith("ALTER TABLE"):
            command_type = "ALTER TABLE (Schema Modification)"
        elif upper_sql.startswith("DROP"):
            command_type = "DROP (Schema Deletion)"
        elif upper_sql.startswith("WITH"):
            command_type = "WITH (Common Table Expression / CTE)"

        # 2. Extract Tables and Joins
        table_matches = re.findall(r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z0-9_.\"']+)", code, re.I)
        unique_tables = list(dict.fromkeys(t.replace('"', '').replace("'", "") for t in table_matches))

        # Joins detection
        joins_found = re.findall(r"\b(INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN\s+([a-zA-Z0-9_]+)", code, re.I)

        # Aggregations detection
        agg_functions = re.findall(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", upper_sql)
        unique_aggs = sorted(set(agg_functions))

        # 3. Critical Safety & Optimization Diagnostics
        # Check for DELETE without WHERE
        if upper_sql.startswith("DELETE") and "WHERE" not in upper_sql:
            diagnostics.append(DiagnosticItem(
                id="diag-sql-delete-no-where",
                title="Critical Data Safety: DELETE without WHERE clause",
                severity="error",
                explanation="Executing a DELETE statement without a WHERE clause permanently deletes ALL rows in the table.",
                recommended_correction="Add a WHERE clause specifying the exact primary key or condition for deletion.",
                corrected_snippet=f"{clean_sql} WHERE id = :target_id;",
                detection_type="static_sql_safety_check"
            ))

        # Check for UPDATE without WHERE
        if upper_sql.startswith("UPDATE") and "WHERE" not in upper_sql:
            diagnostics.append(DiagnosticItem(
                id="diag-sql-update-no-where",
                title="Critical Data Safety: UPDATE without WHERE clause",
                severity="error",
                explanation="Executing an UPDATE statement without a WHERE clause overwrites column values across EVERY row in the entire table.",
                recommended_correction="Add a WHERE clause to restrict the update to intended records.",
                corrected_snippet=f"{clean_sql} WHERE id = :target_id;",
                detection_type="static_sql_safety_check"
            ))

        # Check for SELECT *
        if re.search(r"\bSELECT\s+\*\s+FROM\b", upper_sql):
            diagnostics.append(DiagnosticItem(
                id="diag-sql-select-star",
                title="Performance Best Practice: SELECT * in production query",
                severity="suggestion",
                explanation="'SELECT *' retrieves all columns including unused text/blob fields. In production, this causes extra I/O, prevents covering index optimizations, and degrades network transfer speeds.",
                recommended_correction="Explicitly enumerate only the specific columns needed by the application (e.g. SELECT id, name, email FROM...).",
                corrected_snippet=re.sub(r"\bSELECT\s+\*\s+FROM\b", "SELECT id, name FROM", clean_sql, flags=re.I),
                detection_type="static_sql_optimizer"
            ))

        # Check for Cartesian product (multiple tables in FROM separated by commas without JOIN)
        if re.search(r"\bFROM\s+[a-zA-Z0-9_]+\s*,\s*[a-zA-Z0-9_]+", code, re.I) and "WHERE" not in upper_sql:
            diagnostics.append(DiagnosticItem(
                id="diag-sql-cartesian-product",
                title="Query Warning: Implicit Cross Join / Cartesian Product",
                severity="warning",
                explanation="Using comma-separated tables in the FROM clause without join conditions creates a Cartesian product, multiplying all rows of table A by all rows of table B.",
                recommended_correction="Use explicit ANSI JOIN syntax with an ON clause (e.g. FROM tableA JOIN tableB ON tableA.id = tableB.a_id).",
                detection_type="static_sql_linter"
            ))

        # Variable/Table items
        variables_functions: List[VariableFunctionItem] = []
        for tbl in unique_tables[:8]:
            variables_functions.append(VariableFunctionItem(
                name=tbl,
                kind="Database Table",
                data_type="Relation",
                description=f"Queried table in relational schema.",
                scope="Database Catalog"
            ))

        for j_type, j_tbl in joins_found[:5]:
            j_name = (j_type.strip() if j_type else "INNER") + " JOIN"
            variables_functions.append(VariableFunctionItem(
                name=f"{j_name} {j_tbl}",
                kind="Relational Join",
                data_type="Table Combination",
                description=f"Combines records based on relational foreign keys.",
                scope="Query Plan"
            ))

        for agg in unique_aggs:
            variables_functions.append(VariableFunctionItem(
                name=f"{agg}()",
                kind="Aggregate Function",
                data_type="Scalar Metric",
                description=f"Computes mathematical aggregate over grouped rows.",
                scope="SELECT Projection"
            ))

        # Line-by-line explanation
        line_by_line: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            exp = "SQL statement clause."
            su = s.upper()
            if su.startswith("SELECT"):
                exp = "SELECT clause specifying which columns or computed expressions to return."
            elif su.startswith("FROM"):
                exp = "FROM clause designating the primary source table."
            elif "JOIN" in su:
                exp = "Relational JOIN clause combining rows from two tables based on matching keys."
            elif su.startswith("WHERE") or "WHERE " in su:
                exp = "WHERE filter clause restricting returned rows to those matching conditions."
            elif su.startswith("GROUP BY"):
                exp = "GROUP BY clause grouping identical rows to calculate aggregate metrics (SUM, COUNT, AVG)."
            elif su.startswith("HAVING"):
                exp = "HAVING clause filtering grouped records after aggregation."
            elif su.startswith("ORDER BY"):
                exp = "ORDER BY clause sorting results ascending (ASC) or descending (DESC)."
            elif su.startswith("LIMIT"):
                exp = "LIMIT clause capping maximum number of records returned to the client."
            elif su.startswith("INSERT INTO"):
                exp = "INSERT INTO clause adding new data rows into target table."
            elif su.startswith("UPDATE"):
                exp = "UPDATE clause designating target table for in-place column modification."
            elif su.startswith("SET"):
                exp = "SET clause specifying new values assigned to columns."
            elif su.startswith("DELETE FROM"):
                exp = "DELETE FROM clause specifying target table to delete rows from."

            line_by_line.append(LineExplanation(line_number=idx, code_segment=s, explanation=exp))

        # Overview
        table_summary = f"table(s) {', '.join(unique_tables)}" if unique_tables else "database relations"
        overview = (
            f"SQL {command_type} statement operating on {table_summary}. "
            f"{f'Combines records using {len(joins_found)} JOIN operation(s). ' if joins_found else ''}"
            f"{f'Calculates aggregate metrics using {', '.join(unique_aggs)}. ' if unique_aggs else ''}"
            f"{'Applies filtering conditions via WHERE/HAVING. ' if 'WHERE' in upper_sql or 'HAVING' in upper_sql else ''}"
            "Defines relational data querying or modification logic."
        )

        logic_workflow = (
            "1. FROM & JOIN: Database engine identifies tables and evaluates join conditions.\n"
            "2. WHERE: Evaluates boolean filter expressions to discard non-matching rows.\n"
            "3. GROUP BY: Partitions remaining rows into aggregate groups.\n"
            "4. HAVING: Filters aggregated groups against group condition predicates.\n"
            "5. SELECT: Evaluates expressions, aliases, and selects output columns.\n"
            "6. DISTINCT: Discards duplicate result tuples if specified.\n"
            "7. ORDER BY: Sorts the final result dataset according to sort criteria.\n"
            "8. LIMIT / OFFSET: Paginates and returns the restricted row subset."
        )

        concepts = [
            "Relational Algebra & Set Theory",
            "Relational JOIN Types (Inner/Left/Right)",
            "Query Logical Execution Order",
            "Aggregate Data Summarization",
            "Index-Driven Search Optimization"
        ]

        limitations = [
            "Performance depends heavily on presence of appropriate B-Tree / Hash indexes on WHERE and JOIN columns.",
            "Queries without LIMIT on large production tables may consume extensive database buffer pool memory.",
            "Execution requires an active relational database instance (PostgreSQL, SQLite, MySQL) with existing schemas."
        ]

        return AnalysisResult(
            overview=overview,
            logic_workflow=logic_workflow,
            line_by_line=line_by_line[:40],
            inputs="Relational database tables, schema columns, indexes, and runtime filter parameter values.",
            outputs="Tabular result set (rows and columns) or affected row count returned to application.",
            variables_functions=variables_functions,
            programming_concepts=concepts,
            limitations=limitations,
            complexity=ComplexityInfo(
                time="O(log N) with B-Tree Index / O(N) full table scan",
                space="O(R) where R is matching row count in memory",
                explanation="SQL runtime complexity depends on table indexes, statistics, and query execution plans (Nested Loop, Hash Join, or Merge Join)."
            ),
            learning_takeaway="SQL execution does not follow the lexical order of the code. The database engine evaluates FROM and JOINs first, then filters with WHERE, groups with GROUP BY, and evaluates SELECT expressions near the end.",
            diagnostics=diagnostics,
            suggested_code=None,
            explanation_of_changes=None,
            mode="local"
        )
