from unittest.mock import MagicMock, patch

from ses.agent import RAG


def test_rag_forces_embedded_engine_without_environment_ordering():
    fake_engine = MagicMock()
    with patch("ses.agent.OfflineRAGEngine", return_value=fake_engine) as engine:
        rag = RAG()
        assert rag.engine is fake_engine

    engine.assert_called_once_with(embedded=True)
