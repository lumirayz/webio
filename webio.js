/*
		WebIO
	
	Author: Lumirayz
	Email: lumirayz@gmail.com
	Depends on: Prototype
*/

/*
	Copyright (C) 2011 by Lumirayz

	Permission is hereby granted, free of charge, to any person obtaining a copy
	of this software and associated documentation files (the "Software"), to deal
	in the Software without restriction, including without limitation the rights
	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the Software is
	furnished to do so, subject to the following conditions:

	The above copyright notice and this permission notice shall be included in
	all copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
	THE SOFTWARE.
*/

var webio = {
	Session: function(node) {
		var self = this;
		self.node = node;
		self.open = false;
		self.session = null;
		
		self.start = function(msg) {
			if(self.open) {throw "trying to open an already open session";}
			new Ajax.Request(node + "/start", {
				method: "post",
				parameters: $H({init: msg}),
				onSuccess: function(resp) {
					var msg = webio.parseMessage(resp.responseText);
					if(msg.type == 3) { //woah, somehow our request got denied
						self.onDenied(msg.data);
						return;
					}
					self.open = true;
					self.session = msg.data;
					self.onAccepted();
					self._poll();
				},
				onFailure: function(resp) {
					self.onConnectFail();
				}
			});
		};
		self.send = function(msg) {
			if(!self.open) {throw "trying to send a message on a closed session";}
			new Ajax.Request(node + "/msg", {
				method: "post",
				parameters: $H({session: self.session, msg: msg}),
				onSuccess: function() {}
			});
		}
		self.close = function() {
			if(!self.open) {throw "trying to close an already closed session";}
			new Ajax.Request(node + "/end", {
				method: "post",
				parameters: $H({session: self.session}),
				onSuccess: function() {}
			});
			self.open = false;
			self.onDisconnect();
		};
		
		self._poll = function() {
			if(!self.open) {return;}
			setTimeout(function() {
				new Ajax.Request(node + "/poll", {
					method: "post",
					parameters: $H({session: self.session}),
					onSuccess: function(resp) {
						var msgs = webio.unpackMessages(resp.responseText);
						msgs.each(function(m) {
							var msg = webio.parseMessage(m);
							if(msg.type == 3) { //disconnected
								if(self.open) {
									self.open = false;
									self.onDisconnect();
								}
								return;
							}
							else if(msg.type == 4) { //overenthousiastic polling
								return;
							}
							else if(msg.type == 2) { //woot message
								self.onMessage(msg.data);
							}
							self._poll(); //they see me pollin', they hatin', they trollin'
						});
					},
					onFailure: function(resp) {
						if(self.open) {
							self.open = false;
							self.onDisconnect();
						}
						return;
					}
				});
			}, 0);
		};
		
		self.onAccepted = function() {};
		self.onDenied = function(reason) {};
		self.onConnectFail = function() {};
		self.onMessage = function(msg) {};
		self.onDisconnect = function() {};
	},
	
	packMessages: function(msgs) {
		return msgs.join("\0");
	},
	unpackMessages: function(msgs) {
		return msgs.split("\0");
	},
	makeMessage: function(type, msg) {
		return type + ":" + msg;
	},
	parseMessage: function(msg) {
		var data = msg.split(":");
		return {type: parseInt(data[0]), data: data.slice(1).join(":")};
	}
};
