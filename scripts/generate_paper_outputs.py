# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from pathlib import Path

from reporting import generate


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate final JNCA paper tables and figures from frozen experiment outputs.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-root", default="outputs/jnca_paper_outputs_d2904_t2904")
    args = parser.parse_args()
    result = generate(args.project_root, args.output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("PASS_JNCA_FINAL_TABLES_AND_FIGURES")


if __name__ == "__main__":
    main()
