WebIO
=====

A simple long polling server using twisted. The javascript code depends on prototype.

Example
-------

### Python side ###

	from twisted.internet import reactor
	from twisted.web import server
	import webio
	import random
	
	class EchoResource(webio.WebIOResource):
		def onConnect(session, init):
			if random.randint(0, 10) > 5: return webio.Denied("random error") #will call onDenied in the javascript with "random error" as first argument
			print "session", session.sid, "connected"
		
		def onDisconnect(session):
			print "session", session.sid, "disconnected"
		
		def onMessage(session, message):
			print "session", session.sid, "has sent:", message
			session.send(message) #echo it back
			if message == "quit":
				session.close() #close it
	
	if __name__ == "__main__":
		reactor.listen(8000, server.Site(EchoResource()))
		reactor.run()

### Javascript side ###

	var sess = new webio.Session("/"); //or whatever resource you put EchoResource on
	sess.onAccepted = function() {console.log("connected!");};
	sess.onDenied = function(msg) {console.log("connection rejected, reason: " + msg);};
	sess.onDisconnect = function() {console.log("disconnected!");};
	sess.onMessage = function(msg) {console.log("message received: " + msg);};
	sess.start();
	sess.send("hey there!");
	sess.send("free pizza!");
	sess.send("quit");

License
-------
MIT license (see source)
