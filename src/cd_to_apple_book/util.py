import logging
def setup_logging(level="INFO"):
    logging.basicConfig(level=getattr(logging, level), format="%(asctime)s %(levelname)s %(message)s")
def confirm(prompt):
    input(f"{prompt}\nPress ENTER to continue…")
