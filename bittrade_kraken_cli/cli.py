import dataclasses
import importlib
import urllib.parse
from functools import wraps
from os import getenv
from typing import Union
from reactivex import operators

import requests
from requests.models import Response
from rich.console import Console
from rich.table import Table

console = Console()


def pretty_print(response: Response):
    request: requests.Request = response.request
    console.line()
    if response.ok:
        body = response.json()
        if body['error']:
            style = 'red'
        else:
            style = 'green'
    else:
        style = 'bold red'
    console.rule(request.url, style=style)
    if response.ok:
        console.print_json(response.text)
        console.line()
    else:
        console.print(f'Failed with status {response.status_code}')
    posted_data = urllib.parse.parse_qs(request.body)
    table = Table('Name', 'Value')
    for k, v in posted_data.items():
        if k == 'nonce':
            continue
        table.add_row(k, v[0])
    if len(table.rows):
        console.rule('Data sent:', style='cyan')
        console.print(table)
        console.line()
    console.rule('From request:', style='cyan')
    console.print(request.__dict__)
    console.line(2)



def private(request_function, result_function):
    if not console:
        raise Exception('Private can only be used with the [fire] version of the CLI')
    try:
        module = importlib.import_module(
            getenv('KRAKEN_SIGNATURE_MODULE', 'sign')
        )
        sign = module.sign
    except (ImportError, AttributeError) as exc:
        console.bell()
        console.line()
        console.rule('Kraken signature implementation missing')
        console.print('''
            This library believes in BYOS (Bring Your Own Signature).
            Implement the signing of request yourself and export its module path to env [red]KRAKEN_SIGNATURE_MODULE[/red] (default 'sign.py') 
            See the README for code sample
        ''')
        raise exc

    return request_function().pipe(
        operators.starmap(sign),
        operators.flat_map(result_function)
    )


def kwargs_to_options(dataclass: dataclasses.dataclass, func):
    def fn(**kwargs):
        new_kwargs = {}
        if 'api_key' in kwargs:
            new_kwargs['api_key'] = kwargs.pop('api_key')
        if 'generate_kraken_signature' in kwargs:
            new_kwargs['generate_kraken_signature'] = kwargs.pop('generate_kraken_signature')
        new_kwargs['options'] = dataclass(**kwargs)

        return func(
            **new_kwargs
        )

    return fn

__all__ = [
    "kwargs_to_options",
    "private",
    "pretty_print",
]