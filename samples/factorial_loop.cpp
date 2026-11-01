// C++ Factorial with Loop
// codewise demonstration sample 3

#include <iostream>

using namespace std;

// Calculates factorial of n using a for-loop.
// Uses long long to accommodate rapid factorial growth.
long long computeFactorial(int n) {
    if (n < 0) {
        return -1; // Indicator for invalid input
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
