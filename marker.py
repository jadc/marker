#!/usr/bin/env python3
# marker by jadc
MAX_POINTS = 10
DELAY_SEC = 10

import time, re, logging, argparse, csv, asyncio, tempfile, subprocess
from pathlib import Path

sem = asyncio.Semaphore(1)

def run(argv, cwd=None):
    logging.debug(f"Running {argv} in {cwd}")
    cmd = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if(cmd.stdout):     logging.debug(cmd.stdout)
    if(cmd.returncode): logging.error(f"CODE {cmd.returncode} WITH {argv}\n{cmd.stderr}")
    return cmd

async def grade(ccid: str, repo: str, script_file: str, publish: bool):
    async with sem:
        logging.info(f"Grading {ccid}...")
        with tempfile.TemporaryDirectory() as d:
            logging.debug(f"Created temporary directory, '{d}'")

            # Clone student repository
            cmd = run( ["git", "clone", repo, Path(d)] )
            if(cmd.returncode):
                return (ccid, f"ERROR ({cmd.returncode}) SEE LOG")

            # Run marking script in current directory, giving it submission directory
            cmd = run( ["./" + script_file, Path(d)] )
            if(cmd.returncode):
                return (ccid, f"ERROR ({cmd.returncode}) SEE LOG")
            
            if publish: return (ccid, extract_mark(cmd.stdout), feedback(repo, cmd.stdout))
            else:       return (ccid, extract_mark(cmd.stdout), "Run with '--publish' for feedback")

def extract_mark(stdout: str):
    r = re.search(r"Total: *(\d+)/(\d+)", stdout)
    return round((float(r.group(1)) / float(r.group(2)))*MAX_POINTS, 2)

# Creates issue on GitHub repo containing feedback
# Returns URL to issue
def feedback(repo: str, stdout: str):
    args = ["gh", "issue", "create", "--title", "Feedback", "-R", repo, "-F", "-"]
    cmd = subprocess.run(args, stdout=subprocess.PIPE, input=stdout, text=True)
    url = cmd.stdout.strip().replace("https://", "")
    logging.debug(f"Published feedback to '{url}'; waiting {DELAY_SEC} s to avoid rate limit")
    time.sleep(DELAY_SEC)
    return url

# Read CSV for CCIDs and GitHub repositories
async def gather(csv_file: str, script_file: str, out_file: str, publish: bool):
    with open(Path(csv_file), "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip headings
        submissions = [ grade(x[4], x[6], script_file, publish) for x in reader if x[4] and x[6] ]
    results = await asyncio.gather(*submissions)

    with open(Path(out_file), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["CCID", "Grade", "Feedback"])
        writer.writerows(results)
    logging.info(f"Grades written to '{out_file}'")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=str, help="submissions csv (from 'Download grades' on GitHub Classroom)")
    p.add_argument("script", type=str, help="any script (with a shebang) with first argument being directory to grade")
    p.add_argument("-o", "--output", type=str, default="grades.csv", help="output csv including CCID and corresponding lab grade")
    p.add_argument("--publish", action="store_true", help="publishes feedback to students repos; only use after testing!")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    l = logging.INFO
    if(args.verbose): l = logging.DEBUG
    logging.basicConfig(format='%(asctime)s %(levelname)s | %(message)s', level=l, datefmt='%Y-%m-%d %H:%M:%S')

    if(args.publish): logging.info("PUBLISH MODE!!!")
    asyncio.run(gather(args.csv, args.script, args.output, args.publish))
