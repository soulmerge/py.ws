import tornado.web
import tornado.websocket
import logging
from score.ws._server import WebSocketClient as WebSocketClientBase
import http.cookies


class WebSocketClient(WebSocketClientBase):

    def __init__(self, wshandler, *args, **kwargs):
        self.wshandler = wshandler
        super().__init__(wshandler.server, *args, **kwargs)

    def _send(self, data):
        self.wshandler.write_message(data)

    def _disconnect(self, code, reason):
        self.wshandler.close(code, reason)


class WSHandler(tornado.websocket.WebSocketHandler):

    def __init__(self, *args, **kwargs):
        self.client = None
        self.log = logging.getLogger('%s.%d' % (__name__, id(self)))
        super().__init__(*args, **kwargs)

    def check_origin(self, origin):
        # TODO
        return True

    def open(self):
        # TODO: prevent more than X connects from same client
        self.debug('new connection')
        self.close_code = None
        self.close_reason = None
        session_id = None
        if self.session_cookie:
            cookies = http.cookies.SimpleCookie(
                input=self.request.headers.get('cookie', ''))
            session_id = cookies[self.session_cookie].value
        try:
            self.client = WebSocketClient(self, session_id)
        except Exception as e:
            self.log.exception(e)
            # would love to close the connection at this point, but the
            # browser does not report the correct error code if we do it
            # here. we will instead store the code to send and close the
            # connection on first message.
            # see here for codes:
            # https://tools.ietf.org/html/rfc6455
            self.close_code = 1011
            self.close_reason = 'Error Opening Connection'

    def on_message(self, message):
        print('Received message!', message)
        if self.ws_connection is None:
            # closed connection, ignore message
            return
        if self.close_code is not None:
            self.debug('found close code %d, closing connection' %
                       self.close_code)
            self.close(self.close_code, self.close_reason)
            return
        self.debug('message received %s' % message)
        try:
            self.client._message_received(message)
        except Exception as e:
            self.log.exception(e)
            # see https://tools.ietf.org/html/rfc6455
            self.close(1011, 'Internal Server Error')

    def on_close(self):
        if not self.client:
            return
        self.debug('connection closed')
        self.client.disconnected()

    def write_message(self, msg, *args, **kwargs):
        if self.close_code is not None:
            self.debug('found close code %d, closing connection' %
                       self.close_code)
            self.close(self.close_code, self.close_reason)
            self.debug('sending message ' + msg[:200])
        super().write_message(msg, *args, **kwargs)

    def debug(self, msg):
        self.log.debug(msg)


def run(server, session_cookie='session'):
    class ConfiguredWSHandler(WSHandler):
        @property
        def session_cookie(self):
            return session_cookie
        @property
        def server(self):
            return server
    application = tornado.web.Application([
        ('/', ConfiguredWSHandler),
    ], debug=True)
    application.listen(server.port, address=server.host)
    tornado.ioloop.IOLoop.instance().start()
