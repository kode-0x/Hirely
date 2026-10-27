"""Shared Streamlit UI helpers for the dashboard and every page.

This module centralizes the cross-page presentation concerns: cached
settings/provider construction, the always-visible provider/model/connection
indicator, the session-state keys that carry market research and the selected
model between pages, and the market/salary no-network disclosure banner. Pages
import these helpers so the indicator and session contract stay identical
everywhere.

It imports the provider only through :func:`hirely.providers.factory.build_provider`
and the typed error base :class:`hirely.providers.base.ProviderError`; it never
touches a concrete HTTP client, which keeps ``httpx`` and the concrete adapters
out of the presentation layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from hirely.config import Settings
from hirely.market.research import NO_DATA_DISCLOSURE
from hirely.providers.base import ProviderError
from hirely.providers.factory import build_provider

if TYPE_CHECKING:
    from hirely.providers.base import AIProvider
    from hirely.schemas.market import MarketResearchResult
    from hirely.schemas.provider import ModelInfo

#: Session-state key holding the stored market-research result (core-workflow gate).
RESEARCH_KEY = "market_research_result"

#: Session-state key holding the user-selected model id for the active provider.
MODEL_KEY = "selected_model"

#: Session-state key holding runtime Settings overrides chosen on the Settings page.
OVERRIDES_KEY = "settings_overrides"

PAGE_ICON = "💼"


def load_settings() -> Settings:
    """Load runtime settings, applying session overrides from the Settings page.

    Overrides chosen on the Settings page (provider, Ollama base URL, OpenRouter
    key) are layered over the environment so the user can switch provider and
    model within a session without editing ``.env``. A validation error is
    rendered and the script is stopped.

    Returns:
        The validated :class:`Settings`.
    """
    overrides = st.session_state.get(OVERRIDES_KEY, {})
    try:
        return Settings(**overrides)
    except ValueError as exc:
        st.error(f"Configuration error: {exc}")
        st.stop()
        raise  # pragma: no cover - st.stop halts execution first.


def set_override(key: str, value: object) -> None:
    """Record or clear a single runtime Settings override in session state.

    Args:
        key: The ``Settings`` field name to override.
        value: The override value; an empty value clears the override.
    """
    overrides = dict(st.session_state.get(OVERRIDES_KEY, {}))
    if value in (None, ""):
        overrides.pop(key, None)
    else:
        overrides[key] = value
    st.session_state[OVERRIDES_KEY] = overrides


def get_provider(settings: Settings) -> AIProvider:
    """Build the provider adapter named by the settings.

    Args:
        settings: The validated runtime settings.

    Returns:
        A provider adapter implementing the provider contract.
    """
    return build_provider(settings)


def active_model(settings: Settings) -> str:
    """Return the model to use: the session selection or the configured default.

    Args:
        settings: The validated runtime settings.

    Returns:
        The selected model id, or an empty string when none is chosen yet.
    """
    selected = st.session_state.get(MODEL_KEY, "")
    if selected:
        return str(selected)
    if settings.ai_provider == "ollama":
        return settings.ollama_model
    return settings.openrouter_model


def configure_page(title: str) -> None:
    """Apply the shared page configuration.

    Args:
        title: The page title shown in the browser tab.
    """
    st.set_page_config(page_title=f"Hirely - {title}", page_icon=PAGE_ICON, layout="wide")


def render_provider_indicator(settings: Settings) -> None:
    """Render the always-visible provider/model/connection indicator.

    The indicator shows the selected provider, the active model (or a prompt to
    choose one on Settings), and a live connectivity status from the provider's
    non-billable health check. It is rendered in the sidebar so it appears on
    every page.

    Args:
        settings: The validated runtime settings.
    """
    model = active_model(settings)
    with st.sidebar:
        st.markdown("### Active provider")
        st.write(f"Provider: `{settings.ai_provider}`")
        st.write(f"Model: `{model}`" if model else "Model: not selected (open Settings)")

        try:
            health = get_provider(settings).health()
        except ProviderError as exc:
            st.error(f"Connection: unavailable ({exc})")
            return

        if health.ok:
            st.success("Connection: reachable")
        else:
            st.warning(f"Connection: unavailable. {health.detail or ''}".strip())


def require_model(settings: Settings) -> str | None:
    """Return the active model or render guidance to pick one and return ``None``.

    Args:
        settings: The validated runtime settings.

    Returns:
        The active model id, or ``None`` when no model is selected yet.
    """
    model = active_model(settings)
    if not model:
        st.info("No model selected. Open the Settings page to choose a model before running this tool.")
        return None
    return model


def store_research(result: MarketResearchResult) -> None:
    """Persist a market-research result in session state for downstream pages.

    Args:
        result: The market-research result to store.
    """
    st.session_state[RESEARCH_KEY] = result


def get_research() -> MarketResearchResult | None:
    """Return the stored market-research result, if any.

    Returns:
        The stored :class:`MarketResearchResult`, or ``None`` when absent.
    """
    return st.session_state.get(RESEARCH_KEY)


def require_research() -> MarketResearchResult | None:
    """Gate downstream pages on the market-research-first workflow.

    Returns:
        The stored research result, or ``None`` after rendering a prompt to run
        Market Research first.
    """
    result = get_research()
    if result is None:
        st.warning(
            "Run Market Research first. The core workflow researches the job market before "
            "creating or tailoring a resume. Open the Market Research page to begin."
        )
    return result


def render_no_data_disclosure() -> None:
    """Render the shared no-network disclosure banner."""
    st.warning(NO_DATA_DISCLOSURE)


def mark_free_models(models: list[ModelInfo]) -> tuple[list[str], set[str]]:
    """Split discovered models into display labels and the set of free model ids.

    The free flag comes from the provider's own discovery check (the same
    free verification used before any call), so Settings can mark and filter
    free-verified models and warn on a non-free selection before use.

    Args:
        models: The discovered models from the provider.

    Returns:
        A tuple of ``(labels, free_ids)`` where labels annotate non-free models.
    """
    labels: list[str] = []
    free_ids: set[str] = set()
    for info in models:
        if info.free:
            free_ids.add(info.id)
            labels.append(info.id)
        else:
            labels.append(f"{info.id} (not free)")
    return labels, free_ids
