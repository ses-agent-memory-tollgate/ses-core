"""
Unit tests for embeddings module (Local + Remote providers).
All heavy models are mocked.
"""
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from ses.core.embeddings import (
    BaseEmbeddingModel,
    LocalEmbeddingModel,
    RemoteEmbeddingModel,
    get_embedding_model,
)


class TestLocalEmbeddingModel:
    def test_local_model_encodes(self):
        mock_st = MagicMock()
        mock_st.encode.return_value = np.array([[0.1, 0.2, 0.3]])

        with patch("ses.core.embeddings.SentenceTransformer", return_value=mock_st):
            model = LocalEmbeddingModel(model_name="all-MiniLM-L6-v2", device="cpu")
            result = asyncio.run(model.encode("hello world"))

        # Should return the raw output from encode
        assert result.shape == (1, 3)
        mock_st.encode.assert_called_once()

    def test_local_model_handles_list_input(self):
        mock_st = MagicMock()
        mock_st.encode.return_value = np.array([[0.1], [0.2]])

        with patch("ses.core.embeddings.SentenceTransformer", return_value=mock_st):
            model = LocalEmbeddingModel("test-model")
            result = asyncio.run(model.encode(["a", "b"]))

        assert result.shape == (2, 1)


class TestRemoteEmbeddingModel:
    @pytest.mark.asyncio
    async def test_remote_calls_endpoint_and_parses_list(self):
        mock_response = MagicMock()
        mock_response.json.return_value = [[0.9, 0.1], [0.8, 0.2]]
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            model = RemoteEmbeddingModel(
                endpoint_url="http://embeddings.local/v1/embed",
                api_key="sk-test",
                model_name="my-emb",
            )
            res = await model.encode(["foo", "bar"])

            assert isinstance(res, np.ndarray) or isinstance(res, list)
            mock_client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_remote_raises_on_http_error(self):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            err_resp = MagicMock()
            err_resp.raise_for_status.side_effect = Exception("boom")
            mock_client.post.return_value = err_resp
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            model = RemoteEmbeddingModel(endpoint_url="http://bad")

            with pytest.raises(Exception):
                await model.encode("fail")


class TestEmbeddingFactory:
    def test_factory_defaults_to_local(self):
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "local"}, clear=True):
            with patch("ses.core.embeddings.LocalEmbeddingModel") as mock_local:
                mock_local.return_value = MagicMock(spec=BaseEmbeddingModel)
                model = get_embedding_model()
                mock_local.assert_called_once()

    def test_factory_uses_remote_when_configured(self):
        env = {
            "EMBEDDING_PROVIDER": "remote",
            "EMBEDDING_SERVICE_URL": "https://emb.example.com",
            "EMBEDDING_API_KEY": "k123",
            "EMBEDDING_MODEL": "custom",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("ses.core.embeddings.RemoteEmbeddingModel") as mock_remote:
                mock_remote.return_value = MagicMock(spec=BaseEmbeddingModel)
                model = get_embedding_model()
                mock_remote.assert_called_once_with(
                    endpoint_url="https://emb.example.com",
                    api_key="k123",
                    model_name="custom",
                )

    def test_remote_factory_raises_without_url(self):
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "remote"}, clear=True):
            with pytest.raises(ValueError, match="EMBEDDING_SERVICE_URL"):
                get_embedding_model()
