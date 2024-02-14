#!/usr/bin/env python3
# marker by jadc
MAX_POINTS = 10
FEEDBACK_FILE = "README.md"
BRANCH_NAME = "main"

import sys, re, logging, argparse, csv, tempfile, subprocess
from datetime import datetime
from pathlib import Path

def run(argv, cwd=None):
    logging.debug(f"Running {argv} in {cwd}")
    cmd = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if cmd.stdout:     logging.debug(cmd.stdout)
    if cmd.returncode: logging.error(f"CODE {cmd.returncode} WITH {argv}\n{cmd.stderr}")
    return cmd

def abort(msg: str) -> None:
    print(f"{sys.argv[0]}: {msg}", file=sys.stderr)
    exit(1)

def grade(ccid: str, repo: str):
    logging.info(f"Grading {ccid}...")
    with tempfile.TemporaryDirectory() as d:
        logging.debug(f"Created temporary directory, '{d}'")

        # Clone student repository
        cmd = run( ["git", "clone", repo, Path(d)] )
        if cmd.returncode:
            return (ccid, f"ERROR ({cmd.returncode}) SEE LOG")

        # Get latest commit before deadline
        cmd = run( ["git", "rev-list", "-1", f"--min-age={deadline}", "--", BRANCH_NAME], cwd=d )
        if cmd.returncode:
            return (ccid, f"ERROR ({cmd.returncode}) SEE LOG")
        if not cmd.stdout:
            logging.info("No submission before deadline, skipping...")
            return (ccid, 0.0, "No submission before deadline")
        commit = cmd.stdout.strip()

        # Reset to latest commit before deadline, if specified
        if deadline:
            cmd = run( ["git", "reset", "--hard", commit], cwd=d )
            if cmd.returncode:
                return (ccid, f"ERROR ({cmd.returncode}) SEE LOG")

            logging.debug(f"Reset student repository to {commit}")

        # Run marking script in current directory, giving it submission directory
        try:
            marking_cmd = subprocess.run(["./" + args.script, Path(d)], capture_output=True, text=True, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            return (ccid, "TIMED OUT")
        if marking_cmd.stdout:
            logging.debug(marking_cmd.stdout)
        if marking_cmd.returncode:
            logging.error(f"CODE {cmd.returncode} WITH {argv}\n{cmd.stderr}")
            return (ccid, f"ERROR ({marking_cmd.returncode}) SEE LOG")
        
        # Upload feedback to branch on student repository
        if args.publish:
            # Create empty branch
            run(["git", "switch", "--orphan", "feedback"], cwd=d)

            # Write feedback to file
            with open(Path(d) / FEEDBACK_FILE, "w", encoding="utf-8") as f:
                f.write("```diff\n")
                f.write(marking_cmd.stdout)
                f.write("\n```")

            # Add feedback file
            run(["git", "add", FEEDBACK_FILE], cwd=d)
            run(["git", "commit", "-m", "Feedback"], cwd=d)
            run(["git", "push", "-f", "origin", "feedback"], cwd=d)
            logging.info("Pushed feedback to student's repository")
        
        return (ccid, extract_mark(marking_cmd.stdout), "")

def extract_mark(stdout: str):
    r = re.search(r"Total: *(.+)/(.+)", stdout)
    return round((float(r.group(1)) / float(r.group(2)))*MAX_POINTS, 2)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=str, help="submissions csv (from 'Download grades' on GitHub Classroom)")
    p.add_argument("script", type=str, help="any script (with a shebang) with first argument being directory to grade")
    p.add_argument("-o", "--output", type=str, default="grades.csv", help="output csv including CCID and corresponding lab grade")
    p.add_argument("--deadline", type=str, help="grades latest commit before YYYY-MM-DD at midnight")
    p.add_argument("--publish", action="store_true", help="publishes feedback to students repos; only use after testing!")
    p.add_argument("--timeout", type=int, default=30, help="time in seconds to wait before aborting a command")
    p.add_argument("-v", "--verbose", action="store_true")

    # Globals
    global args
    args = p.parse_args()
    global deadline
    deadline = None

    # Input validation
    if( not Path(args.csv).is_file() ):
        abort(f"{args.csv}: No such file or directory")
    if( not Path(args.script).is_file() ): 
        abort(f"{args.script}: No such file or directory")
    if args.deadline:
        try:
            deadline = datetime.strptime( args.deadline, "%Y-%m-%d" ).timestamp()
        except ValueError:
            abort("Deadline does not match format: YYYY-MM-DD")
        deadline = int(deadline) + 86400  # midnight on deadline date
    else:
        deadline = int( datetime.utcnow().timestamp() )

    # Verbosity flag
    logging.basicConfig(format='%(asctime)s %(levelname)s | %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    if args.verbose: logging.getLogger().setLevel(logging.DEBUG)

    if args.publish: logging.info("PUBLISH MODE!!!")

    # Read CSV for CCIDs and GitHub repositories
    with open(Path(args.csv), "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip headings
        results = [ grade(x[4], x[6]) for x in reader if x[4] and x[6] ]

    with open(Path(args.output), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["CCID", "Grade", "Feedback"])
        writer.writerows(results)
    logging.info(f"Grades written to '{args.output}'")
