from datetime import date, datetime, timedelta


def get_base_date() -> date:
    """
    Parses the base date from command line arguments or defaults to yesterday's date.
    If no base date is provided, it defaults to the current date minus one day.
    Returns:
        datetime.date: The base date for collecting data.
    """
    import argparse

    args = argparse.ArgumentParser()
    args.add_argument("--base_date", type=str, help="Base date in the format 'YYYY-MM-DD'. Defaults to yesterday's date if not provided.")

    if args.parse_args().base_date and not isinstance(args.parse_args().base_date, str):
        raise ValueError("Base date must be a string in the format 'YYYY-MM-DD'")

    if args.parse_args().base_date and not datetime.strptime(args.parse_args().base_date, "%Y-%m-%d"):
        raise ValueError("Base date must be a valid date in the format 'YYYY-MM-DD'")

    if args.parse_args().base_date:
        return datetime.strptime(args.parse_args().base_date, "%Y-%m-%d").date()

    return date.today() - timedelta(days=1)