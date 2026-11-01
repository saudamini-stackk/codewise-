import hashlib
import json
import uuid
import re
from typing import List, Dict, Any, Optional
from ..models import PracticeQuestion, PracticeTest, QuestionEvaluation, PracticeEvaluationResult
from .static_engine import StaticEngine

class PracticeEngine:
    def __init__(self, static_engine: Optional[StaticEngine] = None):
        self.static_engine = static_engine or StaticEngine()

    def generate_practice_test(
        self,
        code: str,
        language: str = "python",
        session_id: Optional[str] = None
    ) -> PracticeTest:
        code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]
        analysis = self.static_engine.analyze(code, language)
        lang = language.lower()

        # Extract features from code & analysis
        has_even_odd = "even" in code.lower() or "% 2" in code
        has_input = "input(" in code or "cin >>" in code or "readline" in code
        has_loops = bool(analysis.loop_details and analysis.loop_details.has_loops)
        has_functions = any(v.kind == "function" for v in analysis.variables_functions)
        expected_io = analysis.expected_io

        questions: List[PracticeQuestion] = []

        # 1. Question 1: Program Purpose (MCQ)
        q1_id = f"q-purpose-{code_hash[:6]}"
        overview_snippet = analysis.overview.split(".")[0] if "." in analysis.overview else analysis.overview
        correct_purpose = overview_snippet.strip()
        if len(correct_purpose) > 140:
            correct_purpose = correct_purpose[:137] + "..."

        distractors_purpose = [
            "Sorts a collection in ascending order using divide-and-conquer strategy.",
            "Implements a binary search tree to store key-value associations.",
            "Calculates the shortest path in a weighted graph using Dijkstra's algorithm."
        ]
        q1_options = [correct_purpose] + distractors_purpose
        import random
        rng = random.Random(code_hash)
        rng.shuffle(q1_options)

        questions.append(PracticeQuestion(
            id=q1_id,
            category="purpose",
            question_type="multiple_choice",
            question="What is the primary computational purpose of this program?",
            options=q1_options,
            correct_answer=correct_purpose,
            explanation=f"Based on static analysis of the source code: {analysis.overview}",
            rubric="Identifies the core algorithm or logic problem solved by the program."
        ))

        # 2. Question 2: Execution & Control Flow (MCQ)
        q2_id = f"q-exec-{code_hash[:6]}"
        if has_loops:
            loop_desc = analysis.loop_details.description if analysis.loop_details else "Iterates through loop"
            q2_question = "How does this program control repetitive execution?"
            q2_correct = f"Uses an iterative loop construct: {loop_desc}."
            q2_options = [
                q2_correct,
                "Uses mutual tail recursion without iteration.",
                "Executes asynchronous event-driven worker threads.",
                "Relies entirely on fixed sequential unconditional statements without loops."
            ]
        elif has_even_odd:
            q2_question = "How does the conditional branch evaluate whether a number is even or odd?"
            q2_correct = "Computes `number % 2 == 0`: if remainder is 0, executes the even branch; otherwise the else branch."
            q2_options = [
                q2_correct,
                "Divides by 2 and checks if the quotient is positive.",
                "Counts the total number of decimal digits in the number.",
                "Converts the integer into binary and compares string lengths."
            ]
        else:
            q2_question = "In what order are the primary program instructions executed?"
            q2_correct = "Sequential top-to-bottom order evaluated expression by expression."
            q2_options = [
                q2_correct,
                "Parallel SIMD vectorized execution across multiple cores.",
                "Reverse bottom-to-top execution via backwards call stack unwinding.",
                "Non-deterministic stochastic dispatch based on OS interrupts."
            ]
        rng.shuffle(q2_options)

        questions.append(PracticeQuestion(
            id=q2_id,
            category="execution",
            question_type="multiple_choice",
            question=q2_question,
            options=q2_options,
            correct_answer=q2_correct,
            explanation="The control flow follows standard structured programming constructs (sequential statements, conditionals, and loops).",
            rubric="Demonstrates understanding of control flow and condition evaluation."
        ))

        # 3. Question 3: Output Prediction (Short Answer)
        q3_id = f"q-outpred-{code_hash[:6]}"
        sample_in = expected_io.sample_input if expected_io and expected_io.sample_input else "10"
        sample_out = expected_io.sample_output if expected_io and expected_io.sample_output else "Program output"

        questions.append(PracticeQuestion(
            id=q3_id,
            category="output_prediction",
            question_type="short_answer",
            question=f"If the program is provided with nominal test input `{sample_in}`, what output is produced?",
            options=None,
            correct_answer=sample_out,
            explanation=f"When `{sample_in}` is processed according to the program logic, the resulting output is: '{sample_out}'.",
            rubric=f"Matches expected value '{sample_out}' or clearly captures key keywords."
        ))

        # 4. Question 4: Error Identification (MCQ)
        q4_id = f"q-error-{code_hash[:6]}"
        if has_input and "int(input(" in code:
            q4_question = "What runtime exception will occur if the user inputs the string 'hello' into this program?"
            q4_correct = "ValueError: invalid literal for int() with base 10: 'hello'"
            q4_options = [
                q4_correct,
                "IndexError: string index out of range",
                "KeyError: 'hello' is not a valid dictionary key",
                "ZeroDivisionError: division by zero in modulo operation"
            ]
        elif any(d.severity == "error" for d in analysis.diagnostics):
            err_diag = next(d for d in analysis.diagnostics if d.severity == "error")
            q4_question = f"Which error condition was identified on line {err_diag.line_number or 'the code'}?"
            q4_correct = f"{err_diag.title}: {err_diag.recommended_correction}"
            q4_options = [
                q4_correct,
                "MemoryLeakError: garbage collection cycle threshold exceeded",
                "DeadlockError: concurrent resource acquisition failure",
                "SegmentationFault: illegal memory dereference at 0x0"
            ]
        else:
            q4_question = "Which potential input condition poses the highest runtime risk in this code?"
            q4_correct = "Non-numeric input or unhandled type conversion when expecting integer values."
            q4_options = [
                q4_correct,
                "Entering an even integer such as 4 or 8.",
                "Using standard UTF-8 console encoding.",
                "Running the program in an interactive terminal session."
            ]
        rng.shuffle(q4_options)

        questions.append(PracticeQuestion(
            id=q4_id,
            category="error_identification",
            question_type="multiple_choice",
            question=q4_question,
            options=q4_options,
            correct_answer=q4_correct,
            explanation="Robust programs must anticipate type mismatches, non-numeric inputs, and boundary errors.",
            rubric="Accurately identifies exception conditions and error causes."
        ))

        # 5. Question 5: Edge-Case Handling (Short Answer)
        q5_id = f"q-edge-{code_hash[:6]}"
        if has_even_odd:
            q5_question = "What happens if the input is 0 or a negative integer (such as -4)? Is it evaluated correctly?"
            q5_correct = "0 is evaluated as even because 0 % 2 == 0. Negative even numbers (e.g. -4) also yield remainder 0 and evaluate as even."
        elif has_loops:
            q5_question = "What happens if the collection or range provided to the loop is empty (length 0)?"
            q5_correct = "The loop condition terminates immediately on the first check, and zero iterations execute."
        else:
            q5_question = "Explain how this program handles boundary or edge-case values."
            q5_correct = "Operates within normal boundaries; extreme inputs or invalid types require defensive exception handling."

        questions.append(PracticeQuestion(
            id=q5_id,
            category="edge_cases",
            question_type="short_answer",
            question=q5_question,
            options=None,
            correct_answer=q5_correct,
            explanation="Edge cases test program resilience at boundary values (zero, negative numbers, empty sequences).",
            rubric="Explains behavior for zero, negative, or empty boundary conditions."
        ))

        return PracticeTest(
            id=f"ptest-{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            code_hash=code_hash,
            questions=questions,
            created_at=analysis.learning_takeaway
        )

    def evaluate_test(
        self,
        test: PracticeTest,
        student_answers: Any
    ) -> PracticeEvaluationResult:
        evaluations: List[QuestionEvaluation] = []
        correct_count = 0
        total_score = 0.0

        ans_map: Dict[str, str] = {}
        if isinstance(student_answers, dict):
            ans_map = {str(k): str(v) for k, v in student_answers.items()}
        elif isinstance(student_answers, list):
            for item in student_answers:
                if isinstance(item, dict) and "question_id" in item:
                    ans_map[str(item["question_id"])] = str(item.get("answer", ""))

        for q in test.questions:
            ans = (ans_map.get(q.id) or "").strip()
            is_correct = False
            score = 0.0
            feedback = ""

            if q.question_type == "multiple_choice":
                # Deterministic check: exact match or option letter/number
                clean_ans = ans.lower().strip()
                clean_correct = q.correct_answer.lower().strip()
                if clean_ans == clean_correct or (len(clean_ans) > 5 and clean_ans in clean_correct) or (len(clean_correct) > 5 and clean_correct in clean_ans):
                    is_correct = True
                    score = 1.0
                    feedback = "Correct! " + q.explanation
                else:
                    is_correct = False
                    score = 0.0
                    feedback = f"Incorrect. The correct answer is: '{q.correct_answer}'. Explanation: {q.explanation}"

            else:
                # Subjective Short-Answer evaluation against rubric & reference answer
                clean_ans = ans.lower().strip()
                clean_ref = q.correct_answer.lower().strip()

                if not clean_ans:
                    is_correct = False
                    score = 0.0
                    feedback = f"No answer provided. Expected: '{q.correct_answer}'. Explanation: {q.explanation}"
                elif clean_ans == clean_ref:
                    is_correct = True
                    score = 1.0
                    feedback = "Excellent! Exact match with the reference answer."
                else:
                    # Token/keyword overlap matching
                    ref_words = set(re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", clean_ref))
                    ans_words = set(re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", clean_ans))
                    overlap = ref_words.intersection(ans_words)
                    overlap_ratio = len(overlap) / len(ref_words) if ref_words else 0.0

                    if overlap_ratio >= 0.45 or any(k in clean_ans for k in ["even", "odd", "0", "zero", "valueerror", "terminate", "loop"]):
                        # Check semantic correctness
                        if ("even" in clean_ref and "even" in clean_ans) or ("valueerror" in clean_ref and "value" in clean_ans):
                            is_correct = True
                            score = 1.0
                            feedback = "Correct! Your response captures the key concepts."
                        else:
                            is_correct = overlap_ratio >= 0.5
                            score = 0.5 if is_correct else 0.0
                            feedback = f"Partially correct. Key points to remember: {q.explanation}"
                    else:
                        is_correct = False
                        score = 0.0
                        feedback = f"Incorrect. Expected answer: '{q.correct_answer}'. Explanation: {q.explanation}"

            if is_correct and score >= 0.5:
                correct_count += 1
            total_score += score

            evaluations.append(QuestionEvaluation(
                question_id=q.id,
                student_answer=ans,
                is_correct=is_correct,
                score=score,
                feedback=feedback,
                reference_answer=q.correct_answer
            ))

        total_q = len(test.questions)
        pct = (total_score / total_q) * 100.0 if total_q > 0 else 0.0

        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()

        return PracticeEvaluationResult(
            id=f"peval-{uuid.uuid4().hex[:12]}",
            test_id=test.id,
            total_questions=total_q,
            correct_count=correct_count,
            score_percentage=round(pct, 1),
            evaluations=evaluations,
            completed_at=now_iso
        )
