import logging

from rich.logging import RichHandler

def setup_logging(logger: logging.Logger, log_level=logging.INFO, rest_log_level=logging.WARNING, websocket_log_level=logging.WARNING):
    logger.setLevel(log_level)
    logger.addHandler(RichHandler(log_level))
    l = logging.getLogger('bittrade_kraken_rest')
    l.setLevel(rest_log_level)
    l.addHandler(RichHandler(rest_log_level))
    l = logging.getLogger('bittrade_kraken_websocket')
    l.setLevel(websocket_log_level)
    l.addHandler(RichHandler(websocket_log_level))