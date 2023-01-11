import inspect
import logging
from os import getenv

import orjson
import sys
from concurrent.futures import ThreadPoolExecutor
import time
from typing import Dict, Literal, List

import fire
import websocket
from bittrade_kraken_websocket.connection.generic import EnhancedWebsocket
from rich.console import Console
from rich.table import Table

from bittrade_kraken_rest import (
    get_account_balance,
    get_open_orders,
    get_server_time,
    get_system_status,
)
from bittrade_kraken_rest.endpoints.private.get_websockets_token import get_websockets_token
from bittrade_kraken_rest.endpoints.raw import raw
from bittrade_kraken_rest.environment.cli import pretty_print, private, kwargs_to_options
from bittrade_kraken_rest.models.private.get_open_orders import GetOpenOrdersOptions

from bittrade_kraken_cli.logging import setup_logging

logger = logging.getLogger(__name__)

setup_logging(
    logger, getenv('LOG_LEVEL', logging.WARNING), getenv('REST_LOG_LEVEL', logging.WARNING), getenv('WEBSOCKET_LOG_LEVEL', logging.WARNING)
)

class Cli:
    @staticmethod
    def get_open_orders(data: Dict = None):
        """

        :param data: Json string in the GetOpenOrdersOptions format; refer https://docs.kraken.com/rest/#tag/User-Data/operation/getOpenOrders
        :return:
        """
        options = data or {}

        return pretty_print(
            private(
                kwargs_to_options(GetOpenOrdersOptions, get_open_orders)
            )
        )(**options)

    @staticmethod
    def get_websockets_token():
        return pretty_print(
            private(get_websockets_token)
        )()

    @staticmethod
    def authenticated_websocket(*channels: List[Literal['ownTrades', 'openOrders']]):
        token = private(get_websockets_token)().get_result().token
        console = Console()
        def on_message(ws, message):
            if message != '{"event":"heartbeat"}':
                console.print_json(message)

        def on_open(ws):
            message = {
                "event": "subscribe",
                "subscription": {
                    "name": "ownTrades",
                    "token": token
                }
            }
            if not channels:
                console.print("Activating token by subbing to ownTrades")
                enhanced.send_json(message)
                message["event"] = "unsubscribe"
                # We should actually wait for the subscription confirmation but it's ok here
                time.sleep(2)
                enhanced.send_json(message)
                console.print("Unsub from ownTrades")
            else:
                for channel in channels:
                    message['subscription']['name'] = channel
                    enhanced.send_json(command)

        def on_close(*args):
            console.rule('Websocket disconnected; exiting')
            sys.exit(1)

        socket_connection = websocket.WebSocketApp("wss://ws-auth.kraken.com", on_message=on_message, on_open=on_open, on_close=on_close)
        enhanced = EnhancedWebsocket(socket_connection, token=token)

        executor = ThreadPoolExecutor()
        executor.submit(socket_connection.run_forever)
        executor.shutdown(wait=False)

        while command := console.input('Send message:\n'):
            if command:
                try:
                    command = orjson.loads(command)
                except:
                    console.print_exception()
                else:
                    enhanced.send_json(command)

    @staticmethod
    def public_websocket():
        console = Console()

        def on_message(ws, message):
            if message != '{"event":"heartbeat"}':
                console.print_json(message)

        def on_close(*args):
            console.rule('Websocket disconnected; exiting')
            sys.exit(1)

        socket_connection = None
        enhanced = EnhancedWebsocket(socket_connection, token='')

        executor = ThreadPoolExecutor()
        executor.submit(socket_connection.run_forever)
        executor.shutdown(wait=False)

        while command := console.input('Send message:\n'):
            if command:
                try:
                    command = orjson.loads(command)
                except:
                    console.print_exception()
                else:
                    enhanced.send_json(command)

    @staticmethod
    def interactive():
        sys.exit(1)
        console = Console()
        while command := console.input('Type endpoint name: [italic]use ? for a list, q to quit[/italic]\n'):
            if command == 'q':
                return
            if command == '?':
                table = Table('Endpoint', 'Description')
                endpoints = sorted([method for method in dir(Cli) if not method.startswith('__')])
                for name in endpoints:
                    method = getattr(Cli, name)
                    table.add_row(name, method.__doc__)
                console.print(table)
            else:
                func = getattr(Cli, command)
                signature = inspect.signature(func)
                if 'data' in signature.parameters:
                    options = json.loads(
                        console.input('Options (json string) ').strip("'")
                    )

                    func(data=options)
                else:
                    func()
                console.line(2)

    @staticmethod
    def get_account_balance():
        return pretty_print(
            private(get_account_balance))()

    @staticmethod
    def get_server_time():
        return pretty_print(get_server_time)()

    @staticmethod
    def get_system_status():
        return pretty_print(get_system_status)()

    @staticmethod
    def raw(privacy: Literal['public', 'private'], url, data):
        if privacy == 'public':
            fn = pretty_print(raw)
        else:
            fn = pretty_print(private(raw))
        return fn(url=url, options=data)


if __name__ == '__main__':
    fire.Fire(Cli)
