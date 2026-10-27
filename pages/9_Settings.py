"""Settings: provider and model selection with connectivity and free-model checks.

Ollama: a configurable base URL, selection from installed models, a
connectivity and model-availability check, and pull guidance when no model is
installed. No model is assumed. OpenRouter: the API key comes from the
environment or a password-masked input, and the model dropdown marks and filters
free-verified models and warns on a non-free selection before any use.
On provider failure a clear error and a deliberate 'switch to Ollama' control
are shown; nothing reroutes automatically.

Discovery and health are never billable and are performed through the provider
factory; this page issues no HTTP itself.
"""

from __future__ import annotations

import streamlit as st

from hirely import ui
from hirely.providers.base import ProviderError
from hirely.schemas.provider import ModelInfo


def _discover(settings: object) -> tuple[list[ModelInfo], str | None]:
    """Discover models and health via the provider (never billable).

    Args:
        settings: The active runtime settings.

    Returns:
        A tuple of the discovered models and an optional error message.
    """
    try:
        provider = ui.get_provider(settings)  # type: ignore[arg-type]
        health = provider.health()
        if not health.ok:
            return [], health.detail or "The provider is not reachable."
        return provider.list_models(), None
    except ProviderError as exc:
        return [], str(exc)


def _switch_to_ollama_control() -> None:
    """Render a deliberate control to switch the active provider to Ollama."""
    if st.button("Switch to Ollama"):
        ui.set_override("ai_provider", "ollama")
        st.rerun()


def _render_ollama(settings: object) -> None:
    """Render Ollama configuration, discovery, and model selection.

    Args:
        settings: The active runtime settings.
    """
    base_url = st.text_input("Ollama base URL", value=settings.ollama_base_url)  # type: ignore[attr-defined]
    ui.set_override("ollama_base_url", base_url)

    models, error = _discover(settings)
    if error:
        st.error(f"Ollama is not reachable: {error}")
        st.info("Install Ollama, run 'ollama serve', then pull a model with 'ollama pull <model>'.")
        return
    if not models:
        st.warning("No models are installed. Pull one with 'ollama pull <model>' and refresh.")
        return

    labels, _free = ui.mark_free_models(models)
    choice = st.selectbox("Installed model", labels)
    st.session_state[ui.MODEL_KEY] = choice
    st.success(f"Selected model: {choice}")


def _render_openrouter(settings: object) -> None:
    """Render OpenRouter configuration with free-model marking and a non-free warning.

    Args:
        settings: The active runtime settings.
    """
    env_key = settings.openrouter_api_key  # type: ignore[attr-defined]
    if env_key:
        st.caption("Using OPENROUTER_API_KEY from the environment.")
    else:
        key_input = st.text_input("OpenRouter API key", type="password")
        ui.set_override("openrouter_api_key", key_input)
        if not key_input:
            st.info("Enter an OpenRouter API key to discover free models.")
            return

    models, error = _discover(settings)
    if error:
        st.error(f"OpenRouter is not reachable: {error}")
        _switch_to_ollama_control()
        return

    labels, free_ids = ui.mark_free_models(models)
    free_only = st.checkbox("Show only free-verified models", value=True)
    visible = [label for label in labels if "(not free)" not in label] if free_only else labels
    if not visible:
        st.warning("No free-verified models are available. Switch to Ollama to continue at zero cost.")
        _switch_to_ollama_control()
        return

    choice = st.selectbox("Model", visible)
    model_id = choice.replace(" (not free)", "")
    if model_id not in free_ids:
        st.warning(
            f"'{model_id}' is not verified free. Hirely will refuse to call it. "
            "Choose a free-verified model or switch to Ollama."
        )
    else:
        st.session_state[ui.MODEL_KEY] = model_id
        st.success(f"Selected free-verified model: {model_id}")


def main() -> None:
    """Render the Settings page."""
    ui.configure_page("Settings")
    settings = ui.load_settings()
    ui.render_provider_indicator(settings)

    st.title("Settings")
    st.caption("Choose the provider and model. Discovery and health checks are never billable.")

    provider = st.radio("AI provider", ["ollama", "openrouter"], index=0 if settings.ai_provider == "ollama" else 1)
    ui.set_override("ai_provider", provider)
    if provider != settings.ai_provider:
        st.rerun()

    if settings.ai_provider == "ollama":
        _render_ollama(settings)
    else:
        _render_openrouter(settings)

    st.divider()
    st.subheader("Current selection")
    st.write(f"Provider: `{settings.ai_provider}`")
    model = ui.active_model(settings)
    st.write(f"Active model: `{model}`" if model else "Active model: not selected")


main()
