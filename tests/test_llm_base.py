from tailorcv.llm import Usage, LLMClient


def test_usage_defaults_have_no_cache_data():
    u = Usage(input_tokens=10, output_tokens=5)
    assert u.input_tokens == 10
    assert u.output_tokens == 5
    assert u.cache_read is None
    assert u.cache_write is None


def test_usage_with_cache_fields():
    u = Usage(input_tokens=10, output_tokens=5, cache_read=3, cache_write=7)
    assert u.cache_read == 3
    assert u.cache_write == 7


def test_llmclient_is_runtime_protocol():
    class Dummy:
        model = "dummy-1"

        def generate(self, system_prompt, user_prompt, kb, cache=False):
            return "html", Usage(input_tokens=1, output_tokens=1)

    assert isinstance(Dummy(), LLMClient)


def test_llmclient_rejects_clients_missing_model():
    """A class without `model` no longer satisfies the Protocol — caught at runtime."""
    class NoModel:
        def generate(self, system_prompt, user_prompt, kb, cache=False):
            return "html", Usage(input_tokens=1, output_tokens=1)

    assert not isinstance(NoModel(), LLMClient)
