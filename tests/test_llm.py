from unittest.mock import patch
from ses.core.llm import LocalLLMProvider

def test_local_llm_provider_initialization():
    provider = LocalLLMProvider(model_override="test-llama")
    assert provider.model == "test-llama"

def test_generate_answer_no_context():
    provider = LocalLLMProvider()
    response = provider.generate_answer("query", [])
    assert "no contiene información suficiente" in response

@patch("ses.core.llm._post_json", return_value={"response": "Respuesta mockeada"})
def test_generate_answer_success(mock_post_json):
    provider = LocalLLMProvider()
    docs = [{"text": "Contexto de prueba", "metadata": {"file_name": "test.txt"}}]

    response = provider.generate_answer("¿Qué es esto?", docs)
    assert response == "Respuesta mockeada"
    mock_post_json.assert_called_once()
