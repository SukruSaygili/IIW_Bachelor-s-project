#!/bin/bash

# Usage message
if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "Usage: $0 input.txt [output.bin]"
    exit 1
fi

INPUT_FILE="$1"

# Optional custom output filename
if [ -n "$2" ]; then
    OUTPUT_BIN="$2"
else
    BASENAME=$(basename "$INPUT_FILE" .txt)
    OUTPUT_BIN="${BASENAME}.bin"
fi

# Log file name based on output binary filename
LOG_FILE="${OUTPUT_BIN%.bin}.log"

# Start logging
echo "Log for processing '$INPUT_FILE'" > "$LOG_FILE"
echo "Output binary: $OUTPUT_BIN" >> "$LOG_FILE"
echo "Generated on: $(date)" >> "$LOG_FILE"
echo "==========================================" >> "$LOG_FILE"

# Step 1: Create binary file
echo "[1] Creating binary output file: $OUTPUT_BIN" | tee -a "$LOG_FILE"
cat "$INPUT_FILE" | tr -d '\n' | fold -w8 | while read b; do printf "%02x\n" $((2#$b)); done | xxd -r -p > "$OUTPUT_BIN"

# Step 2: Run ent
echo -e "\n[2] Running 'ent' test on $OUTPUT_BIN:" | tee -a "$LOG_FILE"
ent "$OUTPUT_BIN" | tee -a "$LOG_FILE"

# Step 3: Count individual bits
echo -e "\n[3] Counting individual bits:" | tee -a "$LOG_FILE"
cat "$INPUT_FILE" | fold -w1 | sort | uniq -c | tee -a "$LOG_FILE"

# Step 4: Count 8-bit blocks
echo -e "\n[4] Counting 8-bit blocks:" | tee -a "$LOG_FILE"
cat "$INPUT_FILE" | fold -w8 | sort | uniq -c | tee -a "$LOG_FILE"

echo -e "\nDone. All results saved to '$LOG_FILE'"
