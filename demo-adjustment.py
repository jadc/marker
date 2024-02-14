#!/usr/bin/env python3
# by jadc

from pathlib import Path
import argparse, csv

def isfloat(num: str):
    try:
        float(num)
        return True
    except:
        return False

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("lab", type=str, help="lab grades csv (from marker.py)")
    p.add_argument("demo", type=str, help="demo grades csv (from the 'Demo Grades' Google Sheet)")
    p.add_argument("-o", "--output", type=str, default="adjusted-grades.csv", help="output csv including CCID and corresponding lab grade")
    args = p.parse_args()

    with open(Path(args.demo), "r", newline="", encoding="utf-8") as f:
        demos = dict((x[0], float(x[2])) for x in csv.reader(f) if x[2] and isfloat(x[2]))

    with open(Path(args.lab), "r", newline="", encoding="utf-8") as f:
        labs = list(csv.reader(f))

    # Tweak lab CSV if matches CCID in demo grade CSV
    for x in labs:
        if x[0] in demos and isfloat(x[1]):
            print(x[0], x[1], "-> ", end="")
            x[1] = round(float(x[1])/2 + demos[x[0]], 2)
            new_score = f"{demos[x[0]]}/5.0"
            print(x[1], f"({new_score})")
            x[2] = f"(Demo: {new_score}) {x[2]}"

    with open(Path(args.output), "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(labs)

    print(f"Joined '{args.lab}' and '{args.demo}' into '{args.output}'")
