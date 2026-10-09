"""The marketing agent's room step, driven through httpx's mock transport so the real client code runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from marketing.agent import (
    AgentState,
    GradedEntry,
    Softmax,
    build_feed,
    request_regrade,
    submission_post_id,
    sync_room,
)
from marketing.engagement import parse_feed

HASH_A, HASH_B, HASH_C = ("sha256:" + c * 64 for c in "abc")


def _state() -> AgentState:
    state = AgentState(league_id="league_1", account="softmaxresearch")
    for content_hash, pv in ((HASH_A, "pv_a"), (HASH_B, "pv_b"), (HASH_C, "pv_c")):
        state.entries[content_hash] = GradedEntry(
            content_hash=content_hash,
            text=f"text {pv}",
            label=pv,
            player_name="p",
            policy_version_id=pv,
            first_seen_round="round_1",
            judge=80.0,
        )
    return state


class FakePlatform:
    """Two pages of league submissions (cursor in a response header), forum posts by id, and a grade endpoint."""

    def __init__(self, scores: dict[str, Any]) -> None:
        self.scores = scores
        self.requests: list[httpx.Request] = []
        self.grade_bodies: list[dict[str, Any]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/api/observatory/v2/league-submissions":
            assert request.url.params["league_id"] == "league_1" and request.url.params["limit"] == "500"
            assert request.headers["Authorization"] == "Bearer tok"
            if request.url.params.get("cursor") is None:
                items = [
                    {"policy_version": {"id": "pv_a"}, "notes": json.dumps({"post_id": "post_a"})},
                    {"policy_version": {"id": "pv_b"}, "notes": '{"post_id": "post_b"}'},
                    {"policy_version": {"id": "pv_never_graded"}, "notes": '{"post_id": "post_x"}'},
                ]
                return httpx.Response(200, json={"items": items}, headers={"X-Next-Cursor": "page2"})
            assert request.url.params["cursor"] == "page2"
            items = [
                {"policy_version": {"id": "pv_c"}, "notes": "free text, no link"},
                {"policy_version_id": "pv_c", "notes": {"post_id": "post_c"}},
            ]
            return httpx.Response(200, json={"items": items})
        if path.startswith("/api/observatory/v2/posts/"):
            post_id = path.rsplit("/", 1)[-1]
            if post_id not in self.scores:
                return httpx.Response(404, json={"detail": "not found"})
            return httpx.Response(200, json=self.scores[post_id])
        if path == "/api/observatory/v2/leagues/league_1/grade":
            self.grade_bodies.append(json.loads(request.content))
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(500, text=f"unexpected {path}")


def _softmax(platform: FakePlatform) -> Softmax:
    return Softmax("tok", transport=httpx.MockTransport(platform.handler))


def test_submission_post_id_reads_the_notes_convention() -> None:
    assert submission_post_id({"notes": '{"post_id": "post_1"}'}) == "post_1"
    assert submission_post_id({"notes": {"post_id": "post_2"}}) == "post_2"
    assert submission_post_id({"notes": '{"post_id": " post_3 "}'}) == "post_3"
    assert submission_post_id({"notes": "just a sentence"}) == ""
    assert submission_post_id({"notes": "{not json"}) == ""
    assert submission_post_id({"notes": '{"other": 1}'}) == ""
    assert submission_post_id({}) == ""


def test_sync_room_builds_the_map_and_reports_changes() -> None:
    platform = FakePlatform({"post_a": {"score": 3}, "post_b": {"post": {"score": -2}}, "post_c": {"score": 7}})
    state = _state()
    softmax = _softmax(platform)

    changed, ships_by_pv = sync_room(state, softmax, "league_1")

    assert ships_by_pv == {"pv_a": 3, "pv_b": 0, "pv_c": 7}
    # pv_b went from nothing to 0 ships: no re-grade needed; the never-graded policy version has no hash and is skipped.
    assert changed == ["pv_a", "pv_c"]
    assert {h: r["ships"] for h, r in state.room.items()} == {HASH_A: 3, HASH_B: 0, HASH_C: 7}
    assert state.room[HASH_A]["post_id"] == "post_a" and state.entries[HASH_A].post_id == "post_a"
    assert state.room[HASH_A]["updated_at"].endswith("Z")
    # Both pages were read; post_x was never asked for (its policy version has no graded entry).
    paths = [r.url.path for r in platform.requests]
    assert paths.count("/api/observatory/v2/league-submissions") == 2
    assert "/api/observatory/v2/posts/post_x" not in paths
    assert paths.count("/api/observatory/v2/posts/post_c") == 1

    # The feed carries the room in the shape the game parses.
    feed = build_feed(state)
    assert feed["room"] == {h: {"ships": r["ships"], "updated_at": r["updated_at"]} for h, r in state.room.items()}
    parsed = parse_feed(json.dumps(feed), source="t")
    assert parsed.available and parsed.ships_for(HASH_A) == 3 and parsed.ships_for(HASH_C) == 7

    # Once the feed is published the ships are remembered; the same ships next cycle change nothing...
    state.room_ships = ships_by_pv
    changed, ships_by_pv = sync_room(state, softmax, "league_1")
    assert changed == []
    # ...and a moved post earns a re-grade; a deleted post drops out of the room without an error.
    platform.scores["post_a"] = {"score": 5}
    del platform.scores["post_c"]
    changed, ships_by_pv = sync_room(state, softmax, "league_1")
    assert changed == ["pv_a"] and ships_by_pv == {"pv_a": 5, "pv_b": 0}
    assert HASH_C not in state.room


def test_request_regrade_adds_room_changes_to_posted_entries() -> None:
    platform = FakePlatform({})
    state = _state()
    state.entries[HASH_B].tweet_id = "1"
    ids = request_regrade(state, _softmax(platform), "league_1", extra_ids=["pv_a", "", "pv_a"])
    assert ids == ["pv_a", "pv_b"]
    assert platform.grade_bodies[0]["policy_version_ids"] == ["pv_a", "pv_b"]
    assert platform.grade_bodies[0]["idempotency_key"].startswith("regrade:")
    assert request_regrade(_state(), _softmax(platform), "league_1") == []


def test_state_round_trips_room_fields(tmp_path: Path) -> None:
    state = _state()
    state.room = {HASH_A: {"ships": 3, "updated_at": "t", "post_id": "post_a", "policy_version_id": "pv_a"}}
    state.room_ships = {"pv_a": 3}
    state.entries[HASH_A].post_id = "post_a"
    path = tmp_path / "state.json"
    state.save(path)
    loaded = AgentState.load(path)
    assert loaded.room == state.room and loaded.room_ships == {"pv_a": 3}
    assert loaded.entries[HASH_A].post_id == "post_a"
    # A state file written before the room existed still loads.
    old = json.loads(path.read_text())
    del old["room"], old["room_ships"]
    for entry in old["entries"].values():
        del entry["post_id"]
    path.write_text(json.dumps(old))
    assert AgentState.load(path).room == {} and AgentState.load(path).entries[HASH_A].post_id == ""
