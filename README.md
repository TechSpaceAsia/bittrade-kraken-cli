# Kraken CLI

CLI for Kraken REST and websockets

## Installation

```poetry add bittrade-kraken-cli``` or ```pip install bittrade-kraken-cli```

## Usage

```python cli.py get_system_status```

## Authentication

When using private endpoints, you will need to set up your own authentication function. This way, our library never has access to your API secret.

1. create a `sign.py` file at the root of the project (same folder as `cli.py`)
2. implement a `sign` function in that file: `def sign(request: PreparedRequest, url: str, data: dict) -> PreparedRequest`
3. the sign function should set the `api-key` and `api-sign` headers per Kraken's requirements.

Example of working `sign.py` file:

```python
from os import getenv
from typing import Any
import urllib, hmac, base64, hashlib
from pathlib import Path
import requests

# Taken (with a minor change on non_null_data) from https://docs.kraken.com/rest/#section/Authentication/Headers-and-Signature
def generate_kraken_signature(urlpath, data, secret):
    non_null_data = {k: v for k, v in data.items() if v is not None}
    post_data = urllib.parse.urlencode(non_null_data)
    encoded = (str(data['nonce']) + post_data).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    signature_digest = base64.b64encode(mac.digest())
    return signature_digest.decode()


def sign(request: requests.PreparedRequest, url: str, data: dict[str, Any]):
    request.headers['API-Key'] = getenv("KRAKEN_API_KEY")
    request.headers['API-Sign'] = generate_kraken_signature(
        url, data,
        getenv("KRAKEN_API_SECRET")
    )
    return request

```
