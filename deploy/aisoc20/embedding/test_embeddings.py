import json
import unittest

import httpx

from aisoc_local_embeddings import (
    DIMENSION,
    MODEL,
    URL,
    embed_vectors,
    validate_vectors,
)


class EmbeddingsContract(unittest.IsolatedAsyncioTestCase):
    async def test_native_route_batches_and_preserves_order(self):
        batches = []

        def respond(request):
            self.assertEqual(str(request.url), URL)
            payload = json.loads(request.content)
            self.assertEqual(payload["model"], MODEL)
            self.assertFalse(payload["truncate"])
            batches.append(payload["input"])
            vectors = [
                [float(int(text) + 1)] + [0.0] * (DIMENSION - 1)
                for text in payload["input"]
            ]
            return httpx.Response(200, json={"model": MODEL, "embeddings": vectors})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            vectors = await embed_vectors([str(n) for n in range(9)], client=client)
        self.assertEqual([len(b) for b in batches], [8, 1])
        self.assertEqual([v[0] for v in vectors], list(range(1, 10)))

    async def test_http_failure_propagates_without_zero_fallback(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(503))
        async with httpx.AsyncClient(transport=transport) as client:
            with self.assertRaises(httpx.HTTPStatusError):
                await embed_vectors(["deployment probe"], client=client)

    def test_invalid_count_dimension_and_zero_are_rejected(self):
        for vectors in ([], [[1.0]], [[0.0] * DIMENSION]):
            with (
                self.subTest(vectors_length=len(vectors)),
                self.assertRaises(ValueError),
            ):
                validate_vectors(vectors, 1)


if __name__ == "__main__":
    unittest.main()
