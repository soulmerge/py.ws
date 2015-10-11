define("%s", ["lib/score/oop", "lib/score/js/excformat", "lib/bluebird"], function(oop, excformat, BPromise) {

    return oop.Class({
        __name__: 'WebSocket',
        __events__: true,

        __static__: {

            connections: {},

            get: function(cls, url) {
                if (!cls.connections[url]) {
                    cls.connections[url] = new cls(url);
                }
                return cls.connections[url];
            }

        },

        __init__: function(self, url) {
            self.url = url;
            self.reconnects = [];
            self.handlers = {
                '__error__': function(exception) {
                    if (!exception.trace) {
                        return
                    }
                    console.error(excformat(exception));
                }
            };
            window.addEventListener('beforeunload', function() {
                self.disconnect();
            });
            self.connect();
            self.log = function() {};
            // self.log = console.log.bind(console);
        },

        register: function(self, channel, handler) {
            if (self.handlers[channel]) {
                throw new Error('Handler for channel "' + channel + '" already registered');
            }
            self.handlers[channel] = handler;
        },

        connect: function(self) {
            if (self.connection) {
                return BPromise.resolve(self.connection);
            }
            if (self.connectPromise) {
                return self.connectPromise;
            }
            if (!self._testReconnectStatus()) {
                self.connectPromise = new BPromise(function(resolve, reject) {
                    reject(new Error('Too many failed connection attempts'));
                });
                return self.connectPromise;
            }
            self.connectPromise = self._establishConnection().then(self._initializeConnection).then(function(connection) {
                self.log('[WS] connected', self.connection);
                self.connectPromise = null;
                self.trigger('connect');
                return connection;
            }).caught(function(error) {
                console.error('Could not connect to websocket', error);
                self.connectPromise = null;
                throw error;
            });
            return self.connectPromise;
        },

        disconnect: function(self) {
            if (!self.connection) {
                return;
            }
            self.connection.onclose = function() {};
            self.connection.close();
            self.connection = null;
        },

        send: function(self, channel, data) {
            var message = JSON.stringify([channel, data]);
            if (self.connection) {
                self.log('[WS] sending', [channel, data]);
                self.connection.send(message);
                return BPromise.resolve();
            }
            return self.connect().then(function(connection) {
                self.log('[WS] sending', [channel, data]);
                connection.send(message);
            });
        },

        _messageReceived: function(self, message) {
            var channel = message[0],
                data = message[1];
            if (!self.handlers[channel]) {
                return
            }
            self.handlers[channel](data);
        },

        _tryConnect: function(self) {
            return new BPromise(function(resolve, reject) {
                var connection = new WebSocket(self.url);
                connection.onopen = function() {
                    connection.onclose = null;
                    connection.onerror = null;
                    resolve(connection);
                };
                connection.onclose = function() {
                    reject('connection rejected');
                };
                connection.onerror = function() {
                    reject('connection error');
                };
            });
        },

        _establishConnection: function(self) {
            self.connectPromise = new BPromise(function(resolve, reject) {
                self._tryConnect().then(function(connection) {
                    resolve(connection);
                }).caught(function() {
                    BPromise.delay(300).then(function() {
                        self._tryConnect().then(function(connection) {
                            resolve(connection);
                        }).caught(function() {
                            BPromise.delay(800).then(function() {
                                self._tryConnect().then(function(connection) {
                                    resolve(connection);
                                }).caught(function(reason) {
                                    reject(new Error(reason));
                                });
                            });
                        });
                    });
                });
            });
            return self.connectPromise;
        },

        _initializeConnection: function(self, connection) {
            self.connection = connection;
            self.connectPromise = null;
            connection.onclose = function(error) {
                self.log('[WS] connection closed');
                self.connection = null;
                self.lastDisconnect = {
                    code: error.code,
                    reason: error.reason,
                    timestamp: error.timeStamp / 1000,
                    type: error.type,
                    wasClean: error.wasClean,
                };
                BPromise.delay(1000).then(function() {
                    self.connect();
                });
            };
            connection.onerror = function() {
                self.connection = null;
                console.warning('websocket connection error', arguments);
            };
            connection.onmessage = function(event) {
                self._messageReceived(JSON.parse(event.data));
            };
            return connection;
        },

        _testReconnectStatus: function(self) {
            if (self.reconnects.length >= 3) {
                if (self.reconnects[0].getTime() + 5000 > new Date().getTime()) {
                    // more than 3 connect attempts within last 5 seconds.
                    console.error('Too many failed connection attempts', self.lastDisconnect);
                    return false;
                }
                self.reconnects.splice(2, 1000);
            }
            self.reconnects.push(new Date());
            return true;
        }

    });

});
