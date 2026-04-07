import sys
from pathlib import Path
from loguru import logger


# Define the path for the log directory
path_log_dir: Path = Path(__file__).resolve().parent.parent.parent / 'data' / 'logs'
path_log_dir.mkdir(parents=True, exist_ok=True)


def setup_logger() -> None:
    """Configures the unified logging system for the entire application.

    Removes default handlers and adds custom ones for both the terminal (stdout/stderr)
    and persistent file storage (e.g., app.log and error.log).
    """
    logger.remove()
    logger.add(
        sys.stderr,
        format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | '
        '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - '
        '<level>{message}</level>',
        colorize=True,
    )
    logger.add(
        path_log_dir / 'app.log',
        level='INFO',
        rotation='10 MB',
        retention='10 days',
        compression='zip',
        colorize=False,
    )
    logger.add(
        path_log_dir / 'error.log',
        level='WARNING',
        rotation='15 MB',
        retention='10 days',
        compression='zip',
        colorize=False,
    )
