"""
Temporary workaround for railtown.engine.embeddings.search_vector_store.

The API may return a JSON root that is not a Python list; the stock SDK maps
that to an empty list. This module mirrors the intended fix: use the decoded
payload as-is (``items = result_data``).

**Remove this module** (and stop calling :func:`apply_railengine_search_patch`)
when ``rail-engine`` includes that behavior upstream.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable, Literal, Optional, Type

import httpx
from pydantic import BaseModel
from railtown.engine.utils import filter_items

import railtown.engine.client as rail_client

if TYPE_CHECKING:
    from railtown.engine.client import Railengine

logger = logging.getLogger("gym_pt.railengine.sdk_patch")


async def _search_vector_store_patched(
    client: Railengine,
    engine_id: Optional[str] = None,
    vector_store: Literal["VectorStore1", "VectorStore2", "VectorStore3"] = "VectorStore1",
    query: str = "",
    filter_fn: Optional[Callable[[Any], bool]] = None,
    model: Optional[Type[BaseModel]] = None,
) -> AsyncIterator[Any]:
    engine_id = engine_id or client.engine_id

    valid_stores = {"VectorStore1", "VectorStore2", "VectorStore3"}
    if vector_store not in valid_stores:
        raise ValueError(f"vector_store must be one of {valid_stores}, got '{vector_store}'")

    endpoint = f"{client.api_url}/api/Engine/{engine_id}/Embeddings/Search"
    headers = client._get_headers()

    json_body = {
        "VectorStore": vector_store,
        "Query": query,
    }

    logger.info(
        "Searching vector store %s for query: %s (engine: %s) [sdk_patch]",
        vector_store,
        query,
        engine_id,
    )

    try:
        response = await client._client.post(
            endpoint, headers=headers, json=json_body, timeout=30.0
        )
        response.raise_for_status()

        result_data = response.json()
        items = result_data

        async for item in filter_items(
            iter(items),
            filter_fn=filter_fn,
            default_model=client.model,
            override_model=model,
        ):
            yield item

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error searching vector store: %s - %s",
            e.response.status_code,
            e.response.text,
        )
        return
    except httpx.RequestError as e:
        logger.error("Request error searching vector store: %s", str(e))
        return
    except Exception as e:
        logger.error("Error searching vector store: %s", str(e), exc_info=True)
        return


def apply_railengine_search_patch() -> None:
    """Patch ``railtown.engine.client.search_vector_store`` (see module docstring)."""
    rail_client.search_vector_store = _search_vector_store_patched
