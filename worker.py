"""Persistent worker for repeated autonomous cycles; run separately from Streamlit."""
import argparse
import time
from engine import init, cycle

p = argparse.ArgumentParser()
p.add_argument('--interval', type=int, default=60, help='Seconds between runs')
p.add_argument('--batch', type=int, default=8)
args = p.parse_args()
init()
print('ReviewLoop worker started. Ctrl+C to stop.', flush=True)
try:
    while True:
        print(cycle(batch_size=args.batch), flush=True)
        time.sleep(max(5, args.interval))
except KeyboardInterrupt:
    print('Stopped.', flush=True)
