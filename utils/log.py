import logging
from logging.handlers import RotatingFileHandler


def init_logger(
    log_file,
    logger_name="",
    file_log_level=logging.DEBUG,
    console_log_level=logging.ERROR,
    size_in_mb=3,
    log_count=5,
):
    """
    Initialize logger
    """
    root_logger_name = logger_name

    # Formatter
    log_fmt = logging.Formatter("[%(asctime)s][%(module)s(%(lineno)d)] %(message)s")

    # Rotating file logger
    rotating_file_handler = None
    if log_file:
        try:
            rotating_file_handler = RotatingFileHandler(
                log_file,
                mode="a",
                maxBytes=size_in_mb * 1024 * 1024,
                backupCount=log_count,
            )
            rotating_file_handler.setLevel(file_log_level)
            rotating_file_handler.setFormatter(log_fmt)
        except Exception as e:
            print("Create RotatingFileHandler failed! err = %s" % e)

    console_handler = None
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_log_level)
    console_handler.setFormatter(log_fmt)

    if rotating_file_handler:
        logging.getLogger(root_logger_name).addHandler(rotating_file_handler)
    if console_handler:
        logging.getLogger(root_logger_name).addHandler(console_handler)

    logging.getLogger(root_logger_name).setLevel(logging.DEBUG)


init_logger(log_file="race.log", logger_name="race")
logger = logging.getLogger("race")

if __name__ == "__main__":
    logger.info("test")
