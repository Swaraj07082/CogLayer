"""Smoke-test DECIDE ops -> memory_store.json, then sync + query Qdrant."""

from __future__ import annotations

import json
from pathlib import Path

from backend.populate_qdrant import main as populate_main
from backend.utils.qdrant_memory import client, query_user_memories
from backend.utils.workers import (
    MEMORY_STORE_PATH,
    apply_tool_calls,
    resolve_user_key,
)

ALEX_UUID = "1668d210-c809-4cce-8f10-d73f68361852"


def snapshot(label: str) -> dict[str, list[dict]]:
    data = json.loads(MEMORY_STORE_PATH.read_text(encoding="utf-8"))
    store = data["memory_store"]
    print(f"\n=== {label} ===")
    for key, memories in store.items():
        print(f"{key}: {len(memories)} memories")
        for memory in memories:
            emb_len = len(memory.get("embedding_vector") or [])
            print(f"  - {memory['id']} | emb={emb_len} | {memory['text']}")
    return store


def assert_embeddings(store: dict[str, list[dict]]) -> None:
    for key, memories in store.items():
        for memory in memories:
            emb = memory.get("embedding_vector") or []
            assert len(emb) == 384, f"{key}/{memory.get('id')} emb dim={len(emb)}"


def test_apply_ops_directly() -> None:
    """Unit-style: ADD / UPDATE / DELETE / NOOP without another LLM extract."""
    print("\n=== Direct apply_tool_calls (ADD/UPDATE/DELETE/NOOP) ===")
    before = json.loads(MEMORY_STORE_PATH.read_text(encoding="utf-8"))
    alex = before["memory_store"]["alex"]
    target_id = alex[0]["id"]
    original_text = alex[0]["text"]

    fake_calls = [
        {
            "name": "NOOP",
            "candidate_fact": "already known",
            "memory_id": target_id,
            "text": None,
            "reason": "test noop",
        },
        {
            "name": "ADD",
            "candidate_fact": "loves hiking",
            "memory_id": None,
            "text": "Alex loves hiking on weekends.",
            "reason": "test add",
        },
        {
            "name": "UPDATE",
            "candidate_fact": "refined coffee",
            "memory_id": target_id,
            "text": "Alex prefers dark roast coffee every morning.",
            "reason": "test update",
        },
    ]

    result = apply_tool_calls(ALEX_UUID, fake_calls)
    print(json.dumps(result, indent=2))
    assert result["memory_count"] == len(alex) + 1

    mid = json.loads(MEMORY_STORE_PATH.read_text(encoding="utf-8"))
    alex_mid = mid["memory_store"]["alex"]
    updated = next(m for m in alex_mid if m["id"] == target_id)
    assert updated["text"] == "Alex prefers dark roast coffee every morning."
    added = [m for m in alex_mid if m["text"] == "Alex loves hiking on weekends."]
    assert len(added) == 1
    added_id = added[0]["id"]

    delete_result = apply_tool_calls(
        ALEX_UUID,
        [
            {
                "name": "DELETE",
                "candidate_fact": "remove hiking",
                "memory_id": added_id,
                "text": None,
                "reason": "test delete",
            },
            {
                "name": "UPDATE",
                "candidate_fact": "restore coffee",
                "memory_id": target_id,
                "text": original_text,
                "reason": "restore after test",
            },
        ],
    )
    print(json.dumps(delete_result, indent=2))

    after = json.loads(MEMORY_STORE_PATH.read_text(encoding="utf-8"))
    alex_after = after["memory_store"]["alex"]
    assert len(alex_after) == len(alex)
    assert next(m for m in alex_after if m["id"] == target_id)["text"] == original_text
    assert all(m["text"] != "Alex loves hiking on weekends." for m in alex_after)
    print("Direct apply_tool_calls: PASS")


def test_tool_pick_pipeline() -> None:
    print("\n=== process_message_pair end-to-end ===")
    before_count = len(
        json.loads(MEMORY_STORE_PATH.read_text(encoding="utf-8"))["memory_store"]["alex"]
    )
    from backend.utils.workers import process_message_pair

    result = process_message_pair(
        ALEX_UUID,
        "What does alex like?",
        "Alex prefers dark roast coffee and is studying computer science.",
    )
    print(
        json.dumps(
            {
                "tool_calls": result["tool_calls"],
                "store_update": result["store_update"],
            },
            indent=2,
        )
    )
    assert "store_update" in result
    assert result["store_update"]["user_key"] == "alex"
    ops = {c["name"] for c in result["tool_calls"]}
    assert ops <= {"ADD", "UPDATE", "DELETE", "NOOP"}
    after_count = len(
        json.loads(MEMORY_STORE_PATH.read_text(encoding="utf-8"))["memory_store"]["alex"]
    )
    added = sum(1 for c in result["tool_calls"] if c["name"] == "ADD")
    deleted = sum(1 for c in result["tool_calls"] if c["name"] == "DELETE")
    assert after_count == before_count + added - deleted
    print("process_message_pair pipeline: PASS")


def test_qdrant_sync_and_ids() -> None:
    print("\n=== Repopulate Qdrant and verify IDs ===")
    populate_main()
    store = json.loads(MEMORY_STORE_PATH.read_text(encoding="utf-8"))["memory_store"]
    store_ids = {m["id"] for m in store["alex"]}

    response = query_user_memories(
        client=client,
        user_id=ALEX_UUID,
        user_message="What does Alex prefer in the morning?",
        limit=5,
    )
    print(f"Qdrant hits for alex: {len(response.points)}")
    for point in response.points:
        payload_id = point.payload.get("id")
        point_id = str(point.id)
        text = point.payload.get("text")
        print(f"  - payload.id={payload_id} point.id={point_id} | {text}")
        assert payload_id in store_ids, f"payload id {payload_id} missing from store"
        assert point_id == payload_id, f"point.id {point_id} != payload.id {payload_id}"
    print("Qdrant ID sync: PASS")


def main() -> None:
    snapshot("before tests")
    assert_embeddings(json.loads(MEMORY_STORE_PATH.read_text(encoding="utf-8"))["memory_store"])
    print(f"resolve_user_key: {resolve_user_key(ALEX_UUID)}")

    test_apply_ops_directly()
    snapshot("after direct apply (restored)")

    test_tool_pick_pipeline()
    store = snapshot("after tool_pick")
    assert_embeddings(store)

    test_qdrant_sync_and_ids()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
