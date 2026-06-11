# [LAB 6] QUALITY MONITORING (TAHAP 5-6)
# Calculate DQ Metrics
def get_accuracy(df):
    return (df['NPWP'].str.len() == 15).mean() * 100

print(f"Final Accuracy: {get_accuracy(golden_record):.2f}%")
