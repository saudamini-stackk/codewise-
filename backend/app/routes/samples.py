from typing import List, Dict, Any
from fastapi import APIRouter

router = APIRouter(prefix="/api/samples", tags=["Samples"])

SAMPLES_DATA: List[Dict[str, Any]] = [
    {
        "id": "sample-python-even-odd",
        "title": "Python: Even or Odd Checker",
        "language": "python",
        "filename": "even_odd_checker.py",
        "description": "Demonstrates interactive console input, integer typecasting, the modulo arithmetic operator (%), conditional branching (if/else), and input validation boundaries.",
        "code": '''# Python Even-or-Odd Checker
# codewise demonstration sample 1

def check_even_odd(number):
    """
    Evaluates whether an integer is even or odd using the modulo operator.
    An even number yields a remainder of 0 when divided by 2.
    """
    if number % 2 == 0:
        return f"{number} is even."
    else:
        return f"{number} is odd."

def main():
    print("=== Even or Odd Checker ===")
    user_input = input("Enter an integer: ")
    num = int(user_input)
    result = check_even_odd(num)
    print(result)

if __name__ == "__main__":
    main()
'''
    },
    {
        "id": "sample-js-average-bug",
        "title": "JavaScript: Array Average (with Off-by-One Bug)",
        "language": "javascript",
        "filename": "calculate_average_bug.js",
        "description": "Calculates the arithmetic mean of an array with an intentional off-by-one loop boundary error (i <= numbers.length) that introduces undefined and produces NaN.",
        "code": '''// JavaScript Array Average Calculator
// codewise demonstration sample 2 (with intentional off-by-one error)

function calculateAverage(numbers) {
    let sum = 0;

    // INTENTIONAL MISTAKE: i <= numbers.length
    // In JavaScript, array indices range from 0 to numbers.length - 1.
    // When i === numbers.length, numbers[i] is undefined.
    // Adding undefined to a number results in NaN!
    for (let i = 0; i <= numbers.length; i++) {
        sum += numbers[i];
    }

    const average = sum / numbers.length;
    return average;
}

const scores = [85, 92, 78, 90, 88];
console.log("Input scores:", scores);
const result = calculateAverage(scores);
console.log("Calculated average:", result); // Notice this outputs: NaN
'''
    },
    {
        "id": "sample-cpp-factorial-loop",
        "title": "C++: Factorial with Iterative Loop",
        "language": "cpp",
        "filename": "factorial_loop.cpp",
        "description": "Demonstrates C++ stream I/O (<iostream>), standard namespace usage, function definitions, loop structures, and integer precision limits.",
        "code": '''// C++ Factorial with Loop
// codewise demonstration sample 3

#include <iostream>

using namespace std;

long long computeFactorial(int n) {
    if (n < 0) {
        return -1;
    }
    long long factorial = 1;
    for (int i = 1; i <= n; ++i) {
        factorial *= i;
    }
    return factorial;
}

int main() {
    int n;
    cout << "Enter a non-negative integer: ";
    if (cin >> n) {
        long long result = computeFactorial(n);
        if (result == -1) {
            cout << "Error: Factorial of negative numbers is undefined." << endl;
        } else {
            cout << n << "! = " << result << endl;
        }
    } else {
        cout << "Invalid input! Please enter a numeric integer." << endl;
    }
    return 0;
}
'''
    },
    {
        "id": "sample-html-card",
        "title": "HTML & CSS: Product Profile Card",
        "language": "html",
        "filename": "profile_card.html",
        "description": "Demonstrates modern HTML5 semantic elements, responsive flexbox layout, CSS variables, and accessibility tags with live Sandboxed Preview.",
        "code": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Developer Profile Card</title>
    <style>
        :root {
            --bg-card: #141414;
            --text-main: #f5f5f5;
            --accent-pink: #ec4899;
            --border-color: #292329;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #090909;
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
        }
        .card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            max-width: 320px;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }
        .avatar {
            width: 72px;
            height: 72px;
            border-radius: 50%;
            background: linear-gradient(135deg, #ec4899, #f472b6);
            margin: 0 auto 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
        }
        h2 { margin: 0 0 6px; font-size: 1.25rem; }
        p { color: #a1a1aa; font-size: 0.88rem; margin: 0 0 16px; }
        .badge {
            background-color: rgba(236, 72, 153, 0.15);
            color: var(--accent-pink);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <article class="card">
        <div class="avatar" role="img" aria-label="Avatar">🚀</div>
        <h2>Alex Mercer</h2>
        <p>Full-Stack Engineer & Prompt Architect</p>
        <span class="badge">Codewise Pro</span>
    </article>
</body>
</html>
'''
    },
    {
        "id": "sample-sql-revenue-query",
        "title": "SQL: Monthly Customer Revenue Query",
        "language": "sql",
        "filename": "monthly_revenue.sql",
        "description": "Calculates monthly customer revenue using INNER JOIN, WHERE date filters, GROUP BY aggregation, and ORDER BY descending sorting.",
        "code": '''-- SQL Monthly Customer Revenue Query
-- Demonstrates Relational Joins, Aggregation (SUM, COUNT), and Filter Criteria

SELECT 
    c.id AS customer_id,
    c.company_name,
    COUNT(o.order_id) AS total_orders,
    SUM(o.order_amount) AS total_spent,
    ROUND(AVG(o.order_amount), 2) AS average_order_value
FROM customers c
INNER JOIN orders o 
    ON c.id = o.customer_id
WHERE o.order_status = 'completed'
  AND o.created_at >= '2026-01-01'
GROUP BY c.id, c.company_name
HAVING SUM(o.order_amount) >= 1000.00
ORDER BY total_spent DESC
LIMIT 50;
'''
    },
    {
        "id": "sample-json-config",
        "title": "JSON: Application Config Payload",
        "language": "json",
        "filename": "app_config.json",
        "description": "Demonstrates valid structured JSON schema validation, nested objects, type serialization, and key-value mapping.",
        "code": '''{
  "application": "codewise",
  "version": "2.4.0",
  "environment": "production",
  "features": {
    "syntax_analysis": true,
    "safe_execution": true,
    "html_preview": true,
    "sqlite_storage": true
  },
  "supported_categories": [
    "programming",
    "web",
    "data",
    "config"
  ],
  "limits": {
    "max_file_size_kb": 250,
    "execution_timeout_seconds": 5
  }
}
'''
    },
    {
        "id": "sample-java-binary-search",
        "title": "Java: Binary Search Algorithm",
        "language": "java",
        "filename": "BinarySearch.java",
        "description": "Demonstrates logarithmic time O(log N) binary search in Java. When executed without a functional JDK installed, Codewise provides honest diagnostic reporting.",
        "code": '''// Java Binary Search Implementation
// Demonstrates O(log N) divide-and-conquer search on sorted array

public class BinarySearch {
    public static int search(int[] arr, int target) {
        int left = 0;
        int right = arr.length - 1;

        while (left <= right) {
            // Avoid overflow compared to (left + right) / 2
            int mid = left + (right - left) / 2;

            if (arr[mid] == target) {
                return mid; // Found target at index mid
            }
            if (arr[mid] < target) {
                left = mid + 1; // Discard left half
            } else {
                right = mid - 1; // Discard right half
            }
        }
        return -1; // Target not found
    }

    public static void main(String[] args) {
        int[] sortedNumbers = {2, 5, 8, 12, 16, 23, 38, 56, 72, 91};
        int target = 23;
        int resultIndex = search(sortedNumbers, target);
        System.out.println("Target " + target + " found at index: " + resultIndex);
    }
}
'''
    }
]

@router.get("", response_model=List[Dict[str, Any]])
def get_samples():
    return SAMPLES_DATA
