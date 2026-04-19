from twisted.internet import defer


class TestCaseDebug:

    def enable_twisted_debug(self):
        defer.setDebugging(True)
        import twisted.internet.base
        twisted.internet.base.DelayedCall.debug = True

    def set_unittest_maxdiff(self, value):
        self.maxDiff = value
        from .utils import assert_equal
        assert_equal.__self__.maxDiff = None
