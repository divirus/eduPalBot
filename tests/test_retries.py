import asyncio
import importlib
import unittest
from unittest.mock import AsyncMock, patch


class RetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_backends_retry_only_transient_failures(self):
        for module_name, backend, error_name in [
            ('gigachat.services', 'gigachat', 'GigaChat'),
            ('services', 'hugging_face', 'HuggingFace'),
        ]:
            module = importlib.import_module(module_name)
            retry = getattr(module, 'retry_query_' + backend)
            transient = getattr(module, 'Retryable' + error_name + 'Error')
            permanent = getattr(module, error_name + 'Error')
            with self.subTest(backend=backend):
                query = AsyncMock(side_effect=[transient('temporary'), 'answer'])
                with patch.object(module, 'query_' + backend, query):
                    self.assertEqual(await retry('prompt', delay=0), 'answer')
                    self.assertEqual(query.await_count, 2)
                query = AsyncMock(side_effect=permanent('rejected'))
                with patch.object(module, 'query_' + backend, query):
                    with self.assertRaises(permanent):
                        await retry('prompt', delay=0)
                    self.assertEqual(query.await_count, 1)
                query = AsyncMock(side_effect=transient('temporary'))
                with patch.object(module, 'query_' + backend, query):
                    with self.assertRaises(transient):
                        await retry('prompt', max_retries=2, delay=0)
                    self.assertEqual(query.await_count, 2)

    async def test_total_deadline_interrupts_slow_requests(self):
        for module_name, backend, error_name in [
            ('gigachat.services', 'gigachat', 'GigaChat'),
            ('services', 'hugging_face', 'HuggingFace'),
        ]:
            module = importlib.import_module(module_name)
            async def slow(*args, **kwargs):
                await asyncio.sleep(10)
            with patch.object(module, 'query_' + backend, slow):
                with self.assertRaises(getattr(module, 'Retryable' + error_name + 'Error')):
                    await getattr(module, 'retry_query_' + backend)(
                        'prompt', total_timeout=0.01, delay=0,
                    )

    def test_entry_points_import_without_credentials(self):
        for name in ['main', 'handlers', 'edu_pal_bot']:
            importlib.import_module(name)


if __name__ == '__main__':
    unittest.main()
