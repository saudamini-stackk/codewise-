# Python Even-or-Odd Checker
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
