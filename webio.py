################################################################
# Info
################################################################
# 	WebIO
#
# Author: Lumirayz
# Email: lumirayz@gmail.com
# Depends on: Twisted

################################################################
# License
################################################################
# Copyright (C) 2011 by Lumirayz
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

################################################################
# Imports
################################################################

####
# Twisted
####
from twisted.internet import reactor, defer
from twisted.web import resource, server
from twisted.python import log

####
# Stdlib
####
import sys
import uuid

################################################################
# Helpers
################################################################

# no idea why twisted uses lists in req.args
def r(args): return dict([(k, v[0]) for k, v in args.items()])

# message constructor and packer
def makemsg(_tp, payload = ""): return "%i:%s" %(_tp, payload)
def packmsg(msgs): return "\0".join(msgs)

# for deferring x seconds
def wait(delay):
	d = defer.Deferred()
	reactor.callLater(delay, d.callback, None)
	return d

################################################################
# Denied
################################################################
class Denied:
	def __init__(self, reason):
		self.reason = reason

################################################################
# Session
################################################################
class Session(object):
	def __init__(self, sid, **data):
		self.data = data or {}
		self.sid = sid
		self.messages = list()
		self.pingCheck = None
		self.open = True
		self.req = None
	
	def _flush(self):
		msgs = packmsg(self.messages)
		del self.messages[:]
		return msgs
		
	def _send(self, msg):
		if not self.open: raise Exception("session not open")
		self.messages.append(msg)
		if self.req:
			self.req.write(self._flush())
			self.req.finish()
	
	def send(self, msg):
		self._send(makemsg(2, msg))
	
	def close(self):
		if not self.open: raise Exception("session not open")
		if self.req:
			self.req.write(makemsg(3))
			self.req.finish()
		self.open = False
		self.parent.onDisconnect(self)
		del self.parent.sessions[self.sid]
	
	def __getitem__(self, itm):
		try:
			return self.data[itm]
		except KeyError:
			return None
	
	def __setitem__(self, itm, new):
		self.data[itm] = new

################################################################
# Resource: START
################################################################
class StartResource(resource.Resource):
	def render_POST(self, req):
		args = r(req.args)
		for i in range(10):
			sid = uuid.uuid4().hex
			if sid not in self.parent.sessions: break
		session = Session(sid)
		session.parent = self.parent
		status = self.parent.onConnect(session, args["init"] or "")
		if isinstance(status, Denied):
			return makemsg(3, status.reason)
		self.parent.sessions[sid] = session
		session.pingCheck = wait(self.parent.PingTimeout)
		def cb(x): session.close()
		session.pingCheck.addCallback(cb)
		session.pingCheck.addErrback(lambda x: None)
		return makemsg(1, sid)

################################################################
# Resource: MESSAGE
################################################################
class MessageResource(resource.Resource):
	def render_POST(self, req):
		args = r(req.args)
		if "session" not in args: return
		session = self.parent.sessions.get(args["session"])
		if session == None: return makemsg(3)
		if "msg" not in args: return
		self.parent.onMessage(session, args["msg"])
		return ""

################################################################
# Resources: POLL
################################################################
class PollResource(resource.Resource):
	def render_POST(self, req):
		args = r(req.args)
		if "session" not in args: return makemsg(3)
		session = self.parent.sessions.get(args["session"])
		if session == None: return makemsg(3)
		if session.req: return makemsg(4)
		if len(session.messages) > 0:
			return session._flush()
		else:
			session.pingCheck.cancel()
			deferred = req.notifyFinish()
			def fini(err):
				session.req = None
				session.pingCheck = wait(self.parent.PingTimeout)
				def cb(x): session.close()
				session.pingCheck.addCallback(cb)
				session.pingCheck.addErrback(lambda x: None)
			deferred.addCallbacks(fini, fini)
			session.req = req
			return server.NOT_DONE_YET

################################################################
# Resource: END
################################################################
class EndResource(resource.Resource):
	def render_POST(self, req):
		args = r(req.args)
		if "session" not in args: return ""
		session = self.parent.sessions.get(args["session"])
		if not session: return ""
		session.close()
		return ""

################################################################
# WebIOResource
################################################################
class WebIOResource(resource.Resource):
	PingTimeout = 10
	
	def __init__(self):
		resource.Resource.__init__(self)
		self.sessions = dict()
		sr = StartResource()
		cr = MessageResource()
		pr = PollResource()
		er = EndResource()
		sr.parent = self
		cr.parent = self
		pr.parent = self
		er.parent = self
		self.putChild("start", sr)
		self.putChild("msg", cr)
		self.putChild("poll", pr)
		self.putChild("end", er)
	
	def closeAll(self):
		for session in list(self.sessions.values()):
			session.close()
	
	def onConnect(self, session, init): pass
	def onMessage(self, session, msg): pass
	def onDisconnect(self, session): pass
