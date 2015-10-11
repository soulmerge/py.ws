from ._server import WebSocketServer
from score.init import ConfiguredModule, parse_dotted_path, parse_bool
import os


defaults = {
    'host': 'localhost',
    'port': 6544,
    'expose': False,
    'virtjs.path': 'ws.js',
    'virtjs.name': 'lib/score/ws',
}


def init(confdict, ctx_conf, js_conf=None):
    conf = dict(defaults.items())
    conf.update(confdict)
    server = parse_dotted_path(conf['server'])
    server.host = conf['host']
    server.port = int(conf['port'])
    server.url = 'ws://%s:%d' % (server.host, server.port)
    if js_conf and conf['virtjs.path']:

        @js_conf.virtjs(conf['virtjs.path'])
        def ws():
            # TODO: next two lines should be outside of function for increased
            # performance
            tpl = open(os.path.join(os.path.dirname(__file__), 'ws.js')).read()
            virtjs = tpl % conf['virtjs.name']
            return virtjs
    ws_conf = ConfiguredWsModule(ctx_conf, server, parse_bool(conf['expose']))
    server.conf = ws_conf
    return ws_conf


class ConfiguredWsModule(ConfiguredModule):

    def __init__(self, ctx_conf, server, expose):
        super().__init__(__package__)
        self.ctx_conf = ctx_conf
        self.server = server
        self.expose = expose


__all__ = ['init', 'WebSocketServer']
