import asyncio
import pytest

from polyester.async_utils import retry, chunk_generator, asyncify_generator, asyncify_function, TaskContext

class FailNTimes:
    def __init__(self, n_failures):
        self.n_failures = n_failures
        self.n_calls = 0

    async def __call__(self, x):
        self.n_calls += 1
        if self.n_calls < self.n_failures:
            raise Exception('Something bad happened')
        else:
            return x + 1


@pytest.mark.asyncio
async def test_retry():
    f_retry = retry(FailNTimes(3))
    assert await f_retry(42) == 43

    with pytest.raises(Exception):
        f_retry = retry(FailNTimes(4))
        assert await f_retry(42) == 43

    f_retry = retry(n_attempts=5)(FailNTimes(5))
    assert await f_retry(42) == 43

    with pytest.raises(Exception):
        f_retry = retry(n_attempts=5)(FailNTimes(6))
        assert await f_retry(42) == 43


async def unchunk_generator(generator):
    ret = []
    async for chunk in generator:
        loop_ret = []
        ret.append(loop_ret)
        try:
            async for value in chunk:
                loop_ret.append(value)
        except:
            loop_ret.append('exc')
            break
    return ret
        

@pytest.mark.asyncio
async def test_chunk_generator():
    async def generator():
        for i in range(10):
            await asyncio.sleep(0.1)
            yield i

    ret = await unchunk_generator(chunk_generator(generator(), 0.33))
    assert ret == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]


@pytest.mark.asyncio
async def test_chunk_generator_raises():
    async def generator_raises():
        yield 42
        raise Exception('foo')

    ret = await unchunk_generator(chunk_generator(generator_raises(), 0.33))
    assert ret == [[42, 'exc']]


@pytest.mark.asyncio
async def test_asyncify_generator():
    @asyncify_generator
    def f(x, n):
        for i in range(n):
            yield x ** i

    ret = []
    async for x in f(42, 3):
        ret.append(x)
    assert ret == [1, 42, 1764]


@pytest.mark.asyncio
async def test_asyncify_generator_raises():
    @asyncify_generator
    def g(x):
        yield x**2
        raise Exception('banana')

    ret = []
    with pytest.raises(Exception) as exc:
        async for x in g(99):
            ret.append(x)
    assert ret == [99 ** 2]


@pytest.mark.asyncio
async def test_asyncify_function():
    @asyncify_function
    def f(x):
        return x ** 3

    assert await f(77) == 77 * 77 * 77


@pytest.mark.asyncio
async def test_task_context():
    async with TaskContext() as task_context:
        t = task_context.create_task(asyncio.sleep(0.1))
        assert not t.done()
        # await asyncio.sleep(0.0)
    await asyncio.sleep(0.0)  # just waste a loop step for the cancellation to go through
    assert t.cancelled()


@pytest.mark.asyncio
async def test_task_context_grace():
    async with TaskContext(grace=0.2) as task_context:
        u = task_context.create_task(asyncio.sleep(0.1))
        v = task_context.create_task(asyncio.sleep(0.3))
        assert not u.done()
        assert not v.done()
    await asyncio.sleep(0.0)
    assert u.done()
    assert v.cancelled()


class MyException(Exception):
    pass


async def raise_my_exception():
    raise MyException()


@pytest.mark.asyncio
async def test_task_context_wait():
    async with TaskContext(grace=0.1) as task_context:
        u = task_context.create_task(asyncio.sleep(1.1))
        v = task_context.create_task(asyncio.sleep(1.3))
        await task_context.wait(u)

    assert u.done()
    assert v.cancelled()

    with pytest.raises(MyException):
        async with TaskContext(grace=0.2) as task_context:
            u = task_context.create_task(asyncio.sleep(1.1))
            v = task_context.create_task(raise_my_exception())
            await task_context.wait(u)

    assert u.cancelled()
    assert v.done()
