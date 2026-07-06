# Fraud Rule Evaluation

## Objective

Evaluate whether interpretable SQL fraud rules can detect injected synthetic fraud while keeping operational false positives low.

## Final Detection Rules

The fraud-monitoring pipeline uses four rule families:

1. **Large transaction rule**  
   Flags approved transactions with an amount of at least $5,000.

2. **Unusual employee-spend rule**  
   Flags approved transactions exceeding an employee's historical mean by more than three standard deviations.

3. **International-risk rule**  
   Flags international approved transactions of at least $1,000.

4. **Burst-level velocity rule**  
   Groups transactions into employee-level bursts separated by no more than 10 minutes.  
   Any burst containing at least three transactions is flagged.

## Synthetic Benchmark

| Metric | Value |
|---|---:|
| Approved transactions scored | 46,092 |
| Ground-truth fraud transactions | 960 |
| Fraud alerts generated | 1,715 |
| True positives | 960 |
| False positives | 755 |
| False negatives | 0 |
| Precision | 55.98% |
| Recall | 100.00% |
| False-positive rate | 1.67% |
| Alert rate | 3.72% |
| Fraud dollars | $4,117,019.81 |
| Fraud dollars captured | $4,117,019.81 |
| Fraud-dollar capture rate | 100.00% |

## Detection by Fraud Type

| Fraud Type | Fraud Transactions | Detected | Recall |
|---|---:|---:|---:|
| Large amount | 500 | 500 | 100.00% |
| International purchase | 300 | 300 | 100.00% |
| Velocity attack | 160 | 160 | 100.00% |

## Experiment: Transaction-Level vs Burst-Level Velocity Detection

The original transaction-level rule counted prior transactions in a 10-minute rolling window. It detected only later transactions in each four-transaction attack burst.

| Method | Velocity Recall | Precision | False-Positive Rate |
|---|---:|---:|---:|
| Transaction-level rule | 46.88% | 100.00% | 0.00% |
| Burst-level grouping | 100.00% | 100.00% | 0.00% |

## Conclusion

Burst-level grouping improved velocity-fraud detection because it labels the complete suspicious burst rather than only the final transactions that cross a rolling-count threshold.

On this synthetic benchmark, the final rule-based system reached 100% recall and 100% fraud-dollar capture. These results should not be interpreted as expected production performance because the fraud generator and detection rules are related by design. A stronger future evaluation would use held-out fraud mechanisms, adversarial variations, and real anonymized transaction data.
