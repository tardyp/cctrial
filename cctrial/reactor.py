from twisted.internet import reactor


class FakeReactor(object):
    """ a fake reactor to fool TrialRunner not to stop the real reactor """
    running = False
    waiting = False

    def run(self):
        self.running = True
        while self.running:
            reactor.iterate()

    def wait(self):
        print "waiting for filesystem change..."
        self.waiting = True
        while self.waiting:
            reactor.iterate(.1)

    def stop(self):
        self.running = False

    def wake(self):
        self.waiting = False

    def spawnProcess(self, *a, **kw):
        return reactor.spawnProcess(*a, **kw)
