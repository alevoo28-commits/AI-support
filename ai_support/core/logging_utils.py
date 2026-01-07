import logging


def setup_logging(log_file: str = "logs_agentes.log") -> None:
    """Configura logging persistente.

    Se mantiene simple para reflejar el comportamiento actual del monolito.
    """
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )


def log_event(msg: str, level: str = "info") -> None:
    if level == "error":
        logging.error(msg)
    elif level == "warning":
        logging.warning(msg)
    else:
        logging.info(msg)
