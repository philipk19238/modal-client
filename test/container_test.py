import pytest

from polyester.container_entrypoint import function
from polyester.proto import api_pb2
from polyester.function import Function


def square(x):
    return x**2


def raises(x):
    raise Exception('Failure!')


class FakeContainerClient:
    def __init__(self):
        self.inputs = [
            (((42,), {}), 'in-123', False),
            (None, None, True),
        ]
        self.outputs = []

    async def function_get_next_input(self, task_id, function_id):
        return self.inputs.pop(0)

    async def function_output(self, input_id, status, data, exception, traceback):
        self.outputs.append((status, data, exception, traceback))


@pytest.mark.asyncio
async def test_container_entrypoint_success():
    client = FakeContainerClient()
    await function(client, 'ta-123', 'fu-123', square)
    assert client.outputs == [
        (api_pb2.GenericResult.Status.SUCCESS, 1764, None, None)
    ]


@pytest.mark.asyncio
async def test_container_entrypoint_failure():
    client = FakeContainerClient()
    await function(client, 'ta-123', 'fu-123', raises)
    assert len(client.outputs) == 1
    assert client.outputs[0][0] == api_pb2.GenericResult.Status.FAILURE
    assert client.outputs[0][1] is None
    assert client.outputs[0][2] == 'Exception(\'Failure!\')'
    assert 'Traceback' in client.outputs[0][3]


def test_import_function_dynamically():
    f = Function.get_function('polyester.test_support', 'square')
    assert f(42) == 42*42
