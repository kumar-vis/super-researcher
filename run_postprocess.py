from __future__ import annotations

import argparse
from pathlib import Path

from superresearcher.postprocess import postprocess_research_runs


def main() -> None:
    parser = argparse.ArgumentParser(description="Post-process and repair Super Researcher 🦸 corpus files.")
    parser.add_argument("--root", default="research_runs", help="Path containing *_Corpus folders.")
    parser.add_argument("--no-refetch", action="store_true", help="Disable targeted re-fetch attempts.")
    args = parser.parse_args()
    summary = postprocess_research_runs(Path(args.root), refetch=not args.no_refetch)
    print(f"Post-processing complete: {summary['root']}")
    print(f"Renamed: {summary['renamed']}")
    print(f"Refetched: {summary['refetched']}")
    print(f"Deleted: {summary['deleted']}")
    print(f"Removed records: {summary['removed_records']}")
    print(f"Markdown regenerated: {summary['markdown_regenerated']}")
    print(f"Still failed: {summary['still_failed']}")


if __name__ == "__main__":
    main()
