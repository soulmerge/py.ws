import abc
import json
import sys
from score.js.exc2json import exc2json
import logging

log = logging.getLogger(__name__)


class WebSocketClient(metaclass=abc.ABCMeta):

    def __init__(self, server, session_id=None):
        self.session_id = session_id
        self.server = server
        self.disconnect_callbacks = []
        try:
            self.server.on_connect(self)
        except Exception:
            self._disconnect(1011, 'Internal Server Error')

    @abc.abstractmethod
    def _send(self, data):
        pass

    @abc.abstractmethod
    def _disconnect(self, code, reason):
        pass

    def _message_received(self, message):
        self.server._message_received(self, message)

    def send(self, channel, message):
        self._send(json.dumps([channel, message]))

    def disconnect(self, code, reason):
        self._disconnect(code, reason)

    def disconnected(self):
        for callback in self.disconnect_callbacks:
            callback(self)

    def on_disconnect(self, callback):
        self.disconnect_callbacks.append(callback)


class WebSocketServer:

    def __init__(self):
        self.handlers = {
            'session': self.handle_session_cmd
        }

    def handle_session_cmd(self, ctx, data):
        if data['command'] == 'set':
            ctx.client.session_id = data['id']
            # terminate current session, if there was one
            try:
                del ctx.session
            except AttributeError:
                pass
            ctx.session_id = data['id']
        else:
            raise Exception('Command %s not implemented' % data['command'])

    def register(self, channel, handler):
        self.handlers[channel] = handler

    def on_connect(self, client):
        pass

    def _message_received(self, client, message):
        channel, data = json.loads(message)
        try:
            if channel not in self.handlers:
                raise Exception()
                client.send('__error__', {
                    'code': 'no-handler',
                    'message': 'No handler for channel %s' % channel,
                })
                return
            self.on_message(client, channel, data)
        except Exception as e:
            log.exception(e)
            client.send('__error__', exc2json(sys.exc_info(), [__file__]))

    def on_message(self, client, channel, data):
        with self.conf.ctx_conf.Context() as ctx:
            ctx.client = client
            ctx.session_id = client.session_id
            self.handlers[channel](ctx, data)
