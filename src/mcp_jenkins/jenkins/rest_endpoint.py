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

ITEM = RestEndpoint('{job_path}/api/json?depth={depth}')
ITEM_LAST_BUILD_NUMBER = RestEndpoint('{job_path}/api/json?tree=lastBuild[number],buildable')
ITEMS = RestEndpoint('{folder}/api/json?tree={query}')
ITEM_CONFIG = RestEndpoint('{job_path}/config.xml')
ITEM_BUILD = RestEndpoint('{job_path}/{build_type}')

QUEUE = RestEndpoint('queue/api/json?depth={depth}')
QUEUE_ITEM = RestEndpoint('queue/item/{id}/api/json?depth={depth}')
QUEUE_CANCEL_ITEM = RestEndpoint('queue/cancelItem?id={id}')

NODE = RestEndpoint('computer/{name}/api/json?depth={depth}')
NODES = RestEndpoint('computer/api/json?depth={depth}')
NODE_CONFIG = RestEndpoint('computer/{name}/config.xml')

VIEW = RestEndpoint('{view_path}/api/json?depth={depth}')
VIEWS = RestEndpoint('api/json?tree=views[name,url]')

BUILD = RestEndpoint('{job_path}/{number}/api/json?depth={depth}')
BUILD_CONSOLE_OUTPUT = RestEndpoint('{job_path}/{number}/consoleText')
BUILD_STOP = RestEndpoint('{job_path}/{number}/stop')
BUILD_REPLAY = RestEndpoint('{job_path}/{number}/replay')
BUILD_PARAMETERS = RestEndpoint('{job_path}/{number}/api/json?tree=actions[parameters[name,value]]')
BUILD_TEST_REPORT = RestEndpoint('{job_path}/{number}/testReport/api/json?depth={depth}')
BUILD_ARTIFACT = RestEndpoint('{job_path}/{number}/artifact/{relative_path}')
BUILD_ARTIFACTS = RestEndpoint('{job_path}/{number}/api/json?tree=artifacts[fileName,relativePath,displayPath]')
BUILD_PENDING_INPUTS = RestEndpoint('{job_path}/{number}/wfapi/pendingInputActions')
BUILD_INPUT = RestEndpoint('{job_path}/{number}/input/{input_id}/{action}')

PLUGIN_LIST = RestEndpoint('pluginManager/api/json?depth={depth}')
PLUGIN_LIST_TREE = RestEndpoint('pluginManager/api/json?tree=plugins[{tree}]')

SCRIPT_TEXT = RestEndpoint('scriptText')
