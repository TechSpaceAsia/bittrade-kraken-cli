from functools import partial
import inspect
import logging
from os import getenv

from reactivex import operators, just, concat
import orjson
import sys
from concurrent.futures import ThreadPoolExecutor
import time
from typing import Any, Dict, Literal, List

from rich.prompt import Confirm

import fire
import websocket
from bittrade_kraken_websocket import (
    public_websocket_connection,
    private_websocket_connection,
    EnhancedWebsocket,
)
from bittrade_kraken_websocket.operators import (
    keep_messages_only,
    filter_new_socket_only
)
from rich.console import Console
from rich.table import Table

from bittrade_kraken_rest import (
    get_account_balance_request,
    get_trade_history_request,
    get_open_orders_request,
    get_system_status,
    get_websockets_token_request,
    send,
    GetOpenOrdersOptions,
    GetTradeHistoryOptions
)
from bittrade_kraken_rest.endpoints.public.server_time import get_server_time_response
from bittrade_kraken_rest.endpoints.public.system_status import get_system_status_response
from bittrade_kraken_cli import pretty_print, private, console_input

from bittrade_kraken_cli.logging import setup_logging


logger = logging.getLogger(__name__)

setup_logging(
    logger, getenv('LOG_LEVEL', logging.WARNING), getenv('REST_LOG_LEVEL', logging.WARNING), getenv('WEBSOCKET_LOG_LEVEL', logging.WARNING)
)

class Cli:
    @staticmethod
    def get_open_orders(data: dict[str, Any] = None):
        """

        :param data: Json string in the GetOpenOrdersOptions format; refer https://docs.kraken.com/rest/#tag/User-Data/operation/getOpenOrders
        :return:
        """
        options = GetOpenOrdersOptions(**(data or {}))

        return pretty_print(
            private(
            partial(get_open_orders_request, ),
                send
            ).run()
        )
        

    @staticmethod
    def get_websockets_token():
        return pretty_print(
            private(
                get_websockets_token_request,
                send
            ).run()
        )

    @staticmethod
    def get_trade_history(data: dict[str, Any] = None):
        options = GetTradeHistoryOptions(**(data or {}))
        options.ofs = options.ofs or 0
        def next_page_and_continue():
            response = private(
                partial(get_trade_history_request, options),
                send
            ).run()
            pretty_print(response)
            if response.json()['result'].get('count') > options.ofs * 50:
                return True
            return False
        while next_page_and_continue():
            input = Confirm.ask(f'Load page {options.ofs+2}?')
            if input:
                options.ofs += 1
            else:
                break
            

    @staticmethod
    def account_transfer(data: Dict):
        """
        Account transfer is undocumented, the format is:
        {"asset": "XXBT", "amount": "1.25", "to": "AA12 N84G ABCD CSIA", "from": "AA06 N84G WXYZ SIYI"
        """
        return pretty_print(
            private(lambda: raw(
                url='/0/private/AccountTransfer', options=data
            ))
        )


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

        socket_connection = public_websocket_connection(reconnect=True)
        socket_connection.pipe(
            # keep_messages_only()
        ).subscribe(on_next=console.print)
        sub = socket_connection.connect()

        def parse_and_send(command: str, enhanced: EnhancedWebsocket):
            if command:
                try:
                    command = orjson.loads(command)
                except:
                    console.print_exception()
                else:
                    enhanced.send_json(command)
        
        new_socket = socket_connection.pipe(
            filter_new_socket_only(),
            operators.share()
        )
        concat(
            new_socket.pipe(
                operators.take(1),
                operators.ignore_elements()
            ),
            console_input(console)
        ).pipe(
            operators.with_latest_from(new_socket),
        ).subscribe(
            on_next=lambda x: parse_and_send(*x),
            on_completed=sub.dispose,
            on_error=lambda exc: console.print('Error on socket %s', exc)
        )

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
        return pretty_print(get_server_time_response().run())

    @staticmethod
    def get_system_status():
        return pretty_print(get_system_status_response().run())

    @staticmethod
    def raw(privacy: Literal['public', 'private'], url, data):
        if privacy == 'public':
            fn = pretty_print(raw)
        else:
            fn = pretty_print(private(raw))
        return fn(url=url, options=data)


if __name__ == '__main__':
    fire.Fire(Cli)
