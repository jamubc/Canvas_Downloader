#!/usr/bin/env python3
"""cross‑platform CLI for downloading canvas course content.

Usage:
    see README.md

"""

import argparse
# Import shared downloader logic (works on both Mac and Windows)
import downloader_shared as downloader


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a specific Canvas course.")
    parser.add_argument("--api-token", required=True, help="Canvas API token with read‑only permissions")
    parser.add_argument("--course-id", required=True, help="Numeric ID of the Canvas course to download")
    parser.add_argument("--output-dir", required=True, help="Directory where files will be saved")
    parser.add_argument("--canvas-url", default="https://canvas.instructure.com", help="Base URL of your Canvas instance (e.g. https://canvas.ubc.ca)")
    parser.add_argument("--no-structure", action="store_true", help="Flatten all module files into a single directory (default: organize by module name)")
    parser.add_argument("--ignore-pattern", action="append", help="Glob pattern to ignore (e.g. '*.md'). Can be specified multiple times.")
    parser.add_argument("--no-optimize", action="store_true", help="Disable parallel downloads and rate-limit optimization (use legacy sequential mode)")
    parser.add_argument("--include-assignments", action="store_true", help="Download assignments and their descriptions/attachments.")
    parser.add_argument("--include-submissions", action="store_true", help="Download user's submissions (e.g. uploaded files, graded PDFs) for assignments.")
    parser.add_argument("--force", action="store_true", help="Force redownload of all files (ignore existing files)")
    args = parser.parse_args()

    # Ensure the output directory exists
    from pathlib import Path
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Append /api/v1 if not present in the custom URL
    base_url = args.canvas_url.rstrip("/")
    if not base_url.endswith("/api/v1"):
        base_url += "/api/v1"

    # Call the downloader (expects a list of course IDs)
    if hasattr(downloader, 'download_specific_courses'):
        import inspect
        sig = inspect.signature(downloader.download_specific_courses)
        
        # Prepare kwargs based on available parameters in the shared downloader
        kwargs = {}
        if 'no_structure' in sig.parameters:
            kwargs['no_structure'] = args.no_structure
        if 'ignore_patterns' in sig.parameters:
            kwargs['ignore_patterns'] = args.ignore_pattern
        if 'optimize' in sig.parameters:
            kwargs['optimize'] = not args.no_optimize
        if 'include_assignments' in sig.parameters:
            kwargs['include_assignments'] = args.include_assignments
        if 'include_submissions' in sig.parameters:
            kwargs['include_submissions'] = args.include_submissions
        if 'force' in sig.parameters:
             kwargs['force'] = args.force
            
        downloader.download_specific_courses([args.course_id], args.api_token, args.output_dir, base_url, **kwargs)


if __name__ == "__main__":
    main()
