import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from benchmark.evaluate import run_evaluation_benchmark

if __name__ == "__main__":
    run_evaluation_benchmark()
