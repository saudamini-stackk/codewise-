// JavaScript Array Average Calculator
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
