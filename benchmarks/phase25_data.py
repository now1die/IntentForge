"""Deterministic reference mutations for the Phase 2.5 development splits."""

import argparse
import json
from random import Random

from .corpus import DATA


SEED = 2517
DEVELOPMENT = DATA / "phase25-development-v1.json"
FINAL = DATA / "phase25-final-v1.json"

SCAFFOLDS = {
    "train": {
        "conditional_update": "if(seed>2){{ {g}+=seed; }} {g}++;",
        "short_loop": "for(int slot=0;slot<3;slot++){{ {g}+=slot; }}",
        "reused_counter": "while(seed>0){{ {g}+=seed; seed--; }} {g}*=2;",
    },
    "validation": {
        "branch_update": "if(limit>3){{ {g}+=limit; }}else{{{g}-=2;}}",
        "nested_control": "while(seed>1){{if(limit>seed){{{g}*=2;}} {g}--;seed--;}}",
    },
    "calibration": {
        "paired_updates": "{{int auxiliary=limit+seed;{g}+=auxiliary;}} {g}++;",
        "loop_condition": "for(int k=1;k<=limit;k++){{if(k%2==0){{{g}+=k;}}}} {g}-=limit;",
    },
    "development": {
        "two_branch_update": "if(seed>limit){{{g}-=limit;}}if(seed!=0){{{g}+=seed*2;}}",
    },
}

NAMES = (
    ("adjusted", "volume", "volum"),
    ("running", "padding", "pading"),
    ("progress", "initial", "initil"),
    ("balance", "quantity", "quantit"),
    ("diagonal", "fallback", "fallbak"),
    ("measure", "sequence", "sequnce"),
)
CATEGORIES = ("VARIABLE_REFERENCE", "MISSING_EXPRESSION", "ARRAY_INDEX", "FUNCTION_ARGUMENT",
              "DECLARATION_TYPE", "MULTIPLE_LOCALIZED")


def _program(family, category, scaffold, index, amount):
    good, bad, typo = NAMES[index]
    if index == len(NAMES) - 1:
        typo = good[:-1]
    name = f"{family}_{index}"
    signature = f"int {name}(int seed,int limit)"
    local = f"int {good}=seed+{amount}; int {bad}=limit-{amount};"
    steps = scaffold.format(g=good)
    prelude = ""
    if category == "VARIABLE_REFERENCE":
        tail, mutated = f"return {good};", f"return {typo};"
    elif category == "MISSING_EXPRESSION":
        tail, mutated = f"return {good};", "return;"
    elif category == "ARRAY_INDEX":
        prelude = f"int bins_{name}[64];"
        tail, mutated = f"return bins_{name}[{good}]+limit;", f"return bins_{name}[{typo}]+limit;"
    elif category == "FUNCTION_ARGUMENT":
        prelude = f"int consume_{name}(int initial,int {good}){{if(initial<0){{return -1;}}return ({good}*2)+initial;}}"
        tail, mutated = f"return consume_{name}(seed,{good});", f"return consume_{name}(seed,{typo});"
    elif category == "DECLARATION_TYPE":
        signature = f"bool {name}(int seed,int limit)"
        local = f"int {good}=seed+{amount}; int {bad}=limit-{amount}; bool ready=seed>limit; bool spare=false;"
        tail = f"if(ready){{{good}++;}} bool chosen=ready; return chosen || ({good}>99);"
        mutated = tail.replace("chosen=ready", f"chosen={good}")
    else:
        prelude = f"int book_{name}[64];"
        tail = f"int pending={good}; return book_{name}[pending]+{bad};"
        mutated = tail.replace(f"={good}", f"={typo}").replace(f"+{bad}", f"+{bad[:-1]}")
        # The final variation would duplicate names in this family.
        if typo == bad[:-1]:
            mutated = tail.replace(f"={good}", f"={good[:-1]}").replace(f"+{bad}", f"+{bad[:-1]}")
    return f"{prelude} {signature}{{{local} {steps} {mutated}}}".strip(), f"{prelude} {signature}{{{local} {steps} {tail}}}".strip()


def generate():
    rng = Random(SEED)
    rows = []
    for split, scaffolds in SCAFFOLDS.items():
        for tag, scaffold in scaffolds.items():
            for category in CATEGORIES:
                family = f"p25_{tag}_{category.lower()}"
                for index in range(len(NAMES)):
                    source, expected = _program(family, category, scaffold, index, rng.randrange(2, 17))
                    rows.append({"id": f"{family}_{index}", "family": family, "split": split, "category": category,
                                 "provenance": "PROJECT_AUTHORED_REFERENCE_MUTATION", "source": source, "accepted": [expected]})
    for split in SCAFFOLDS:
        rows.append({"id": f"p25_{split}_ambiguous", "family": f"p25_{split}_ambiguous", "split": split,
                     "category": "VARIABLE_REFERENCE", "provenance": "PROJECT_AUTHORED_AMBIGUITY",
                     "source": f"int choose_{split}(int start,int stop){{ return stp; }}",
                     "accepted": [], "ambiguous": True})
    # Change the structure of the explicit ambiguity exercises across partitions.
    rows[-4]["source"] = ("int ambiguous_loop(int start,int stop,bool omit){int scratch=start+stop;"
                          "while(scratch>1){if(omit){break;}scratch--;}return stp+scratch;}")
    rows[-3]["source"] = "int ambiguous_guard(int start,int stop,bool ready){if(ready){return stp;}return start+stop;}"
    rows[-2]["source"] = "int ambiguous_update(int start,int stop){stop*=2;int next=stp;return next+1;}"
    rows[-1]["source"] = "int ambiguous_index[4]; int ambiguous_cell(int start,int stop){ return ambiguous_index[stp]; }"
    return {"version": 1, "seed": SEED, "cases": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=type(DEVELOPMENT), default=DEVELOPMENT)
    args = parser.parse_args()
    args.out.write_text(json.dumps(generate(), indent=2) + "\n")
