#!/usr/bin/env python3
# marker by jadc

import logging, argparse, csv, asyncio, tempfile, subprocess
from pathlib import Path
from datetime import datetime

# Configure batch size
sem = asyncio.Semaphore(1)

def run(argv, cwd=None):
    cmd_as_str = " ".join(argv)
    logging.debug(f"Running '{cmd_as_str}' in {cwd}")
    cmd = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if(cmd.stdout): logging.debug(cmd.stdout)
    if(cmd.returncode): logging.error(f"Failed to run '{cmd_as_str}': {cmd.stderr}")
    return cmd.returncode

async def grade(ccid: str, repo: str, script_file: str):
    async with sem:
        logging.info(f"Grading {ccid}...")
        with tempfile.TemporaryDirectory() as d:
            logging.debug(f"Created temporary directory, '{d}'")

            # Clone student repository
            run(["git", "clone", repo, "."], cwd=d) 
            #logging.debug(f"Cloned student repository '{repo}'")

            # Get marking script
            run(["cp", script_file, d])
            #logging.debug("Copied script into marking environment")
            run(["chmod", "+x", script_file], cwd=d)
            #logging.debug("Made script executable")

            # Run marking script
            with open(ccid + ".txt", "a", buffering=1) as f:
                cmd = subprocess.run(argv, stdout=f, cwd=cwd, shell=True)
                if(cmd.returncode): logging.error(f"Failed to run '{' '.join(argv)}' (code {cmd.returncode})")

# Read CSV for CCIDs and GitHub repositories
async def gather(csv_file: str, script_file: str):
    with open(csv_file) as f:
        reader = csv.reader(f)
        next(reader)  # skip headings
        submissions = [ grade(x[4], x[6], script_file) for x in reader if x[4] and x[6] ]
    await asyncio.gather(*submissions)

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)s | %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

    p = argparse.ArgumentParser()
    p.add_argument("csv", type=str, help="submissions csv (from 'Download grades' on GitHub Classroom)")
    p.add_argument("script", type=str, help="any script (with a shebang), run in root of student repo")
    args = p.parse_args()

    asyncio.run(gather(args.csv, args.script))
