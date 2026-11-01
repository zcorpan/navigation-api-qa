"""Run a batch through every setup in chunks: A first (it picks the links the other setups reuse),
then A2, B and C on that chunk while A moves to the next one; D (Safari TP, one session at a time)
works through chunks on its own queue.

Usage: pipeline.py <batch.txt> <outdir> [chunk size] [follower setups, e.g. A2,B,C]
"""
import os
import queue
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
batch, outdir = sys.argv[1], sys.argv[2]
size = int(sys.argv[3]) if len(sys.argv) > 3 else 30
lines = [l for l in open(batch) if l.strip() and not l.startswith('#')]
chunks = []
os.makedirs(os.path.join(outdir, 'chunks'), exist_ok=True)
for i in range(0, len(lines), size):
    p = os.path.join(outdir, 'chunks', f'{i // size:03}.txt')
    open(p, 'w').writelines(lines[i:i + size])
    chunks.append(p)
log = open(os.path.join(outdir, 'pipeline.log'), 'a')


def run(setup, chunk, workers):
    cmd = [sys.executable, '-I', os.path.join(HERE, 'navqa.py'), 'run', setup, chunk, os.path.join(outdir, setup), '--workers', str(workers)]
    if setup != 'A':
        cmd += ['--plan-from', os.path.join(outdir, 'A')]
    subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=HERE)
    print(setup, 'finished', chunk, flush=True)


WORKERS = {'A2': 2, 'B': 2, 'C': 2, 'D': 1}
if len(sys.argv) > 4:
    WORKERS = {k: v for k, v in WORKERS.items() if k in sys.argv[4].split(',')}
queues = {s: queue.Queue() for s in WORKERS}


def follower(setup):
    while True:
        c = queues[setup].get()
        if c is None:
            return
        run(setup, c, WORKERS[setup])


threads = [threading.Thread(target=follower, args=(s,)) for s in WORKERS]
for t in threads:
    t.start()
for c in chunks:
    run('A', c, 3)
    for q in queues.values():
        q.put(c)
for q in queues.values():
    q.put(None)
for t in threads:
    t.join()
print('all done', flush=True)
