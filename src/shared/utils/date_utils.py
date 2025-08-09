from datetime import date, datetime, timedelta
import argparse


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Parse base, start, and end dates for data collection."
    )
    parser.add_argument(
        "--base_date",
        type=str,
        help="Base date in YYYY-MM-DD. Defaults to yesterday if not provided.",
    )
    parser.add_argument(
        "--start_date",
        type=str,
        help="Start date in YYYY-MM-DD. Defaults to base date if not provided.",
    )
    parser.add_argument(
        "--end_date",
        type=str,
        help="End date in YYYY-MM-DD. Defaults to base date if not provided.",
    )
    return parser.parse_args()


def get_base_date() -> date:
    """
    Return the base date parsed from --base_date, or yesterday if not provided.
    Raises ValueError if --base_date is not in YYYY-MM-DD format or not a valid calendar date.
    """
    args = _parse_args()
    if args.base_date:
        try:
            return datetime.strptime(args.base_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("--base_date must be a valid date in YYYY-MM-DD format")
    return date.today() - timedelta(days=1)


def get_start_end_dates() -> tuple[date, date]:
    """
    Parse --start_date and --end_date, defaulting each to base date when not provided.
    Raises ValueError if dates are malformed, invalid, or if start_date > end_date.
    """
    args = _parse_args()

    # Determine start date
    if args.start_date:
        try:
            start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("--start_date must be a valid date in YYYY-MM-DD format")
    else:
        start = get_base_date()

    # Determine end date
    if args.end_date:
        try:
            end = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("--end_date must be a valid date in YYYY-MM-DD format")
    else:
        end = get_base_date()

    # Only error if both start_date and end_date were explicitly provided
    if args.start_date and args.end_date and start > end:
        raise ValueError("start_date cannot be after end_date")

    return start, end
