#!/usr/bin/env python3
# marker by jadc

import logging, argparse, csv, asyncio, tempfile, subprocess
from pathlib import Path
from datetime import datetime

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

            run(["git", "clone", repo, "."], cwd=d) 
            run(["cp", script_file, d])
            run(["chmod", "+x", script_file], cwd=d)

            # Run marking script
            cmd = subprocess.run(["./" + script_file, "."], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=d)

            if(cmd.returncode): 
                logging.error(f"Failed to run marking script (code {cmd.returncode})")
                return (ccid, f"ERROR: {cmd.returncode}")
            if(cmd.stderr): 
                logging.error(f"Failed to run marking script\n{cmd.stderr}")
                return (ccid, f"ERROR: {cmd.stderr}")

            grade = cmd.stdout.strip().split("\n")[-1].split("/")[0]
            return (ccid, grade, cmd.stdout.strip().replace("\n", " "))

# Read CSV for CCIDs and GitHub repositories
async def gather(csv_file: str, script_file: str, out_file: str):
    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip headings
        submissions = [ grade(x[4], x[6], script_file) for x in reader if x[4] and x[6] ]
    results = await asyncio.gather(*submissions)

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["CCID", "Grade", "Feedback"])
        writer.writerows(results)
    logging.info(f"Grades written to '{out_file}'")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=str, help="submissions csv (from 'Download grades' on GitHub Classroom)")
    p.add_argument("script", type=str, help="any script (with a shebang), run in root of student repo")
    p.add_argument("-o", "--output", type=str, default="grades.csv", help="output csv including CCID and corresponding lab grade")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    l = logging.INFO
    if(args.verbose): l = logging.DEBUG
    logging.basicConfig(format='%(asctime)s %(levelname)s | %(message)s', level=l, datefmt='%Y-%m-%d %H:%M:%S')

    asyncio.run(gather(args.csv, args.script, args.output))
