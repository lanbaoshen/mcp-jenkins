from string import Formatter


class RestEndpoint(str):
    def __new__(cls, value: str) -> str:
        obj = str.__new__(cls, value)
        obj._fields = {name for _, name, _, _ in Formatter().parse(value) if name}
        return obj

    def __call__(self, **kwargs: str | int) -> str:
        if missing := self._fields.difference(kwargs):
            raise KeyError(f'Missing: {missing}')

        return self.format(**kwargs)


CRUMB = RestEndpoint('crumbIssuer/api/json')

ITEM = RestEndpoint('{folder}job/{name}/api/json?depth={depth}')
ITEMS = RestEndpoint('{folder}/api/json?tree={query}')
ITEM_CONFIG = RestEndpoint('{folder}job/{name}/config.xml')
ITEM_BUILD = RestEndpoint('{folder}job/{name}/{build_type}')

QUEUE = RestEndpoint('queue/api/json?depth={depth}')
QUEUE_ITEM = RestEndpoint('queue/item/{id}/api/json?depth={depth}')
QUEUE_CANCEL_ITEM = RestEndpoint('queue/cancelItem?id={id}')

NODE = RestEndpoint('computer/{name}/api/json?depth={depth}')
NODES = RestEndpoint('computer/api/json?depth={depth}')
NODE_CONFIG = RestEndpoint('computer/{name}/config.xml')

BUILD = RestEndpoint('{folder}job/{name}/{number}/api/json?depth={depth}')
BUILD_CONSOLE_OUTPUT = RestEndpoint('{folder}job/{name}/{number}/consoleText')
BUILD_STOP = RestEndpoint('{folder}job/{name}/{number}/stop')
BUILD_REPLAY = RestEndpoint('{folder}job/{name}/{number}/replay')
BUILD_TEST_REPORT = RestEndpoint('{folder}job/{name}/{number}/testReport/api/json?depth={depth}')
