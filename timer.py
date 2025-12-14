import asyncio

class DisconnectTimer:
    '''
    Disconnects.
    executes the function after the timer expires.
    '''

    def __init__(self, timeout: int, callback, *args):
        self.timeout = timeout
        self.callback = callback
        self.args = args
        self.task = asyncio.ensure_future(self.job())

    async def job(self):
        await asyncio.sleep(self.timeout)
        await self.callback(*self.args)

    def cancel(self):
        self.task.cancel()