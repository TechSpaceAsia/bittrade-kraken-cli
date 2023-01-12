from reactivex import Observable, from_iterable, empty, throw
from rich.console import Console

def console_input(console: Console) -> Observable[str]:
    def listen_to_input():
        while True:
            try:
                yield console.input('Send message: \n')
            except KeyboardInterrupt:
                print('Interrupted')
                return empty()
    return from_iterable(listen_to_input())