from collections import deque


class FakeRandomizer:
    def __init__(self, values):
        self.values = deque(values)
        self.calls = 0

    def randint(self, _a, _b):
        self.calls += 1
        return self.values.popleft()
