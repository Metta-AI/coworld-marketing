"""Softmax Video Marketing game container.

Game-hosted Coworld: each seat's player file is a video (or a zip with entry.json + video). The game validates,
measures and judges every entry, publishes the jury to the global viewer, writes per-seat logs and artifacts, then
the replay (the jury page data) and results.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
import zipfile
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Response, WebSocket
from fastapi.responses import HTMLResponse

from videomarketing import __version__
from videomarketing.config import GameConfig
from videomarketing.entry import Entry, EntryMeta, load_entry
from videomarketing.io import artifact_method, decode_replay_bytes, read_data, uri_to_path, write_data
from videomarketing.judge import (
    CraftReview,
    ModelClient,
    TechnicalReview,
    combine,
    craft_review,
    technical_review,
)
from videomarketing.probe import Measurement, contact_sheet, frame_at, measure

logger = logging.getLogger("videomarketing.game")
STATIC_DIR = Path(__file__).parent / "static"
REPLAY_VERSION = 1


@dataclass
class Seat:
    slot: int
    name: str
    file_uri: str = ""
    log_uri: str = ""
    artifact_uri: str = ""
    content_hash: str = ""
    size_bytes: int = 0
    status: str = "waiting"  # waiting | intake | judging | judged | failed
    entry: Entry | None = None
    measurement: Measurement | None = None
    technical: TechnicalReview | None = None
    craft: CraftReview | None = None
    craft_unavailable: bool = False
    score: float = 0.0
    poster_b64: str = ""
    sheet_b64: str = ""
    end_b64: str = ""
    log_lines: list[str] = field(default_factory=list)
    workdir: Path | None = None

    def log(self, message: str) -> None:
        self.log_lines.append(f"{time.strftime('%H:%M:%S')} {message}")

    def public(self, *, include_notes: bool) -> dict[str, Any]:
        meta = self.entry.meta if self.entry else EntryMeta(title=self.name)
        m = self.measurement
        data: dict[str, Any] = {
            "slot": self.slot,
            "name": self.name,
            "status": self.status,
            "title": meta.title,
            "format": meta.format,
            "post": meta.post,
            "alt_text": meta.alt_text,
            "thesis": meta.thesis,
            "credits": meta.credits,
            "made_with": meta.made_with,
            "kind": self.entry.kind if self.entry else "",
            "duration": round(m.duration, 2) if m else None,
            "width": m.width if m else None,
            "height": m.height if m else None,
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "poster": self.poster_b64,
            "score": round(self.score, 2),
            "eligible": bool(self.technical and self.technical.eligible),
        }
        if include_notes:
            data["technical"] = self.technical.to_dict() if self.technical else None
            data["craft"] = self.craft.to_dict() if self.craft else None
            data["craft_unavailable"] = self.craft_unavailable
            data["problems"] = list(self.entry.problems) if self.entry else []
            data["measurement"] = m.to_dict() if m else None
            data["sheet"] = self.sheet_b64
        return data


class Runtime:
    def __init__(
        self,
        config: GameConfig | None,
        *,
        seats_doc: dict[str, Any] | None = None,
        replay: dict[str, Any] | None = None,
    ):
        self.config = config
        self.replay = replay
        self.replay_mode = replay is not None
        self.seats: list[Seat] = []
        self.seats_doc = seats_doc or {}
        self.player_status_uri = self.seats_doc.get("player_status_uri", "")
        self.phase = "replay" if self.replay_mode else "waiting"
        self.started = False
        self.done = self.replay_mode
        self.results: dict[str, Any] | None = replay.get("results") if replay else None
        self.events: list[dict[str, Any]] = []
        self.global_viewers: set[WebSocket] = set()
        self.player_sockets: dict[int, set[WebSocket]] = {}
        self._task: asyncio.Task[None] | None = None
        self.tmp = Path(tempfile.mkdtemp(prefix="svm-"))
        self.media: dict[int, bytes] = {}
        self.on_complete: Any = None
        self.finished_at: float | None = None
        if config is not None:
            for slot, player in enumerate(config.players):
                self.seats.append(Seat(slot=slot, name=player.name))
            for seat_doc in self.seats_doc.get("seats", []):
                slot = int(seat_doc["slot"])
                if 0 <= slot < len(self.seats):
                    seat = self.seats[slot]
                    seat.file_uri = seat_doc.get("file_uri", "")
                    seat.log_uri = seat_doc.get("log_uri", "")
                    seat.artifact_uri = seat_doc.get("artifact_uri", "")
                    seat.content_hash = seat_doc.get("content_hash", "")
                    seat.size_bytes = int(seat_doc.get("size_bytes", 0))

    # ------------------------------------------------------------------ lifecycle

    async def startup(self) -> None:
        if self.replay_mode or self.config is None:
            return
        self.started = True
        self._task = asyncio.create_task(self._guarded_episode())

    async def shutdown(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        shutil.rmtree(self.tmp, ignore_errors=True)

    async def _guarded_episode(self) -> None:
        try:
            await self.run_episode()
        except Exception:  # noqa: BLE001
            logger.exception("episode failed")
            raise

    # ------------------------------------------------------------------ episode

    async def run_episode(self) -> None:
        assert self.config is not None
        cfg = self.config
        self.phase = "intake"
        await self.publish({"type": "phase", "phase": self.phase})
        for seat in self.seats:
            await asyncio.to_thread(self._intake, seat)
            await self.publish({"type": "seat", "seat": seat.public(include_notes=False)})

        self.phase = "judging"
        await self.publish({"type": "phase", "phase": self.phase})
        client = ModelClient(cfg.judge) if cfg.judge.mode == "panel" else None
        if cfg.judge.mode == "panel" and client is not None and not client.available:
            logger.warning("judge mode is panel but no model endpoint is configured; craft panel unavailable")
        judged_by_hash: dict[str, Seat] = {}
        for seat in self.seats:
            seat.status = "judging"
            await self.publish({"type": "seat", "seat": seat.public(include_notes=False)})
            twin = judged_by_hash.get(seat.content_hash) if seat.content_hash else None
            if twin is not None and twin.technical is not None:
                seat.technical, seat.craft, seat.craft_unavailable = twin.technical, twin.craft, twin.craft_unavailable
                seat.log("identical bytes to an earlier seat; judgement copied")
            else:
                await asyncio.to_thread(self._judge, seat, client)
                if seat.content_hash:
                    judged_by_hash[seat.content_hash] = seat
            seat.score = combine(seat.technical, seat.craft, cfg.judge) if seat.technical else 0.0
            seat.status = "judged" if seat.technical and seat.technical.eligible else "failed"
            seat.log(f"score {seat.score:.1f} (technical {seat.technical.score if seat.technical else 0:.0f}, "
                     f"craft {seat.craft.score if seat.craft else 'n/a'})")
            await self.publish({"type": "seat", "seat": seat.public(include_notes=True)})

        self.phase = "complete"
        self.results = self._results()
        await self.publish({"type": "final", "results": self.results})
        await asyncio.to_thread(self._write_outputs)
        self.done = True
        self.finished_at = time.monotonic()
        await self._notify_players_final()
        logger.info("episode complete scores=%s feed_pick=%s", self.results["scores"], self.results["feed_pick"])
        if cfg.linger_seconds:
            await asyncio.sleep(cfg.linger_seconds)
        if self.on_complete is not None:
            outcome = self.on_complete()
            if outcome is not None:
                await outcome

    def _intake(self, seat: Seat) -> None:
        assert self.config is not None
        seat.status = "intake"
        seat.workdir = self.tmp / f"seat{seat.slot}"
        seat.workdir.mkdir(parents=True, exist_ok=True)
        path = uri_to_path(seat.file_uri) if seat.file_uri else None
        if path is None and seat.file_uri:
            staged = seat.workdir / "file"
            try:
                staged.write_bytes(read_data(seat.file_uri))
                path = staged
            except Exception as error:  # noqa: BLE001
                seat.log(f"could not fetch player file: {error}")
                path = None
        if path is None or not path.exists():
            problem = "fatal: no player file staged for this seat"
            seat.entry = Entry(EntryMeta(title=seat.name), None, "invalid", [problem])
            seat.log(seat.entry.problems[0])
            return
        if not seat.content_hash:
            seat.content_hash = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if not seat.size_bytes:
            seat.size_bytes = path.stat().st_size
        seat.entry = load_entry(path, seat.workdir, self.config.limits, default_title=seat.name)
        for problem in seat.entry.problems:
            seat.log(problem)
        if seat.entry.video_path is None:
            return
        seat.measurement = measure(seat.entry.video_path)
        seat.log(f"measurement: {json.dumps(seat.measurement.to_dict())}")
        if not seat.measurement.ok:
            return
        m = seat.measurement
        poster = seat.workdir / "poster.jpg"
        if frame_at(seat.entry.video_path, min(m.duration * 0.4, max(m.duration - 0.5, 0)), poster):
            seat.poster_b64 = base64.b64encode(poster.read_bytes()).decode()
        sheet = seat.workdir / "sheet.jpg"
        if contact_sheet(seat.entry.video_path, m.duration, self.config.judge.frames, sheet):
            seat.sheet_b64 = base64.b64encode(sheet.read_bytes()).decode()
        end = seat.workdir / "end.jpg"
        if frame_at(seat.entry.video_path, max(m.duration - 1.0, 0), end):
            seat.end_b64 = base64.b64encode(end.read_bytes()).decode()
        with suppress(OSError):
            self.media[seat.slot] = seat.entry.video_path.read_bytes()

    def _judge(self, seat: Seat, client: ModelClient | None) -> None:
        assert self.config is not None
        cfg = self.config
        entry = seat.entry or Entry(EntryMeta(title=seat.name), None, "invalid", ["fatal: no entry"])
        m = seat.measurement or Measurement(ok=False, error="not measured")
        seat.technical = technical_review(entry, m, cfg.limits)
        for check in seat.technical.failures:
            seat.log(f"technical: {check.id} failed: {check.detail}")
        if not seat.technical.eligible:
            seat.log("ineligible: a hard gate failed")
            return
        if client is None:
            return
        sheet = (seat.workdir or self.tmp) / "sheet.jpg"
        end = (seat.workdir or self.tmp) / "end.jpg"
        if not sheet.exists():
            seat.craft_unavailable = True
            seat.log("craft panel skipped: no contact sheet")
            return
        seat.craft = craft_review(client, entry, m, sheet, end if end.exists() else None, cfg.brief, slot=seat.slot)
        if seat.craft is None:
            seat.craft_unavailable = client.available
            seat.log("craft panel unavailable; scored on the technical panel only")
        else:
            seat.log(f"craft: {json.dumps(seat.craft.to_dict())}")

    # ------------------------------------------------------------------ outputs

    def _results(self) -> dict[str, Any]:
        assert self.config is not None
        cfg = self.config
        eligible = [bool(s.technical and s.technical.eligible) for s in self.seats]
        scores = [round(s.score, 2) for s in self.seats]
        postable = [e and s.score >= cfg.judge.postable_threshold for s, e in zip(self.seats, eligible, strict=True)]
        candidates = [s.slot for s, p in zip(self.seats, postable, strict=True) if p]
        feed_pick = max(candidates, key=lambda i: scores[i]) if candidates else None
        craft_values = [None if s.craft is None else round(s.craft.score, 1) for s in self.seats]
        if cfg.judge.mode == "technical":
            judge_mode = "technical"
        elif all(c is None for c in craft_values):
            judge_mode = "technical-fallback"
        else:
            judge_mode = "panel"
        return {
            "scores": scores,
            "eligible": eligible,
            "technical": [round(s.technical.score, 1) if s.technical else 0.0 for s in self.seats],
            "craft": craft_values,
            "postable": postable,
            "player_names": [s.name for s in self.seats],
            "titles": [(s.entry.meta.title if s.entry else s.name) for s in self.seats],
            "formats": [(s.entry.meta.format if s.entry else "other") for s in self.seats],
            "durations_seconds": [round(s.measurement.duration, 2) if s.measurement else 0.0 for s in self.seats],
            "verdicts": [(s.craft.verdict if s.craft else self._technical_verdict(s)) for s in self.seats],
            "judge_mode": judge_mode,
            "judge_model": cfg.judge.model if judge_mode == "panel" else "",
            "feed_pick": feed_pick,
            "top_score": max(scores) if scores else 0.0,
            "brief": cfg.brief,
        }

    @staticmethod
    def _technical_verdict(seat: Seat) -> str:
        if seat.technical is None:
            return "Not judged."
        failures = seat.technical.failures
        if not seat.technical.eligible:
            return "Ineligible: " + "; ".join(c.detail for c in failures if c.gate)[:240]
        if not failures:
            return "Technical panel: every check passed."
        return ("Technical panel: " + "; ".join(f"{c.id} ({c.detail})" for c in failures))[:280]

    def replay_payload(self, *, include_media: bool) -> dict[str, Any]:
        assert self.config is not None
        payload: dict[str, Any] = {
            "version": REPLAY_VERSION,
            "game": "softmax-video-marketing",
            "game_version": __version__,
            "config": self.config.model_dump(exclude={"tokens"}),
            "brief": self.config.brief,
            "entries": [s.public(include_notes=True) for s in self.seats],
            "results": self.results,
            "events": [e for e in self.events if e.get("type") != "seat"],
            "media": {},
        }
        if include_media and self.results is not None:
            budget = self.config.replay_media_budget_bytes
            order = sorted(self.seats, key=lambda s: (-s.score, s.slot))
            used = 0
            for seat in order:
                blob = self.media.get(seat.slot)
                if blob is None:
                    continue
                if used + len(blob) > budget:
                    continue
                payload["media"][str(seat.slot)] = base64.b64encode(blob).decode()
                used += len(blob)
        return payload

    def _write_outputs(self) -> None:
        assert self.config is not None and self.results is not None
        # Seat logs and artifacts first (game-hosted contract), then player status, replay, and finally results.
        for seat in self.seats:
            if seat.log_uri:
                text = "\n".join(seat.log_lines) + "\n"
                with suppress(Exception):
                    write_data(seat.log_uri, text, content_type="text/plain")
            if seat.artifact_uri and seat.slot in self.media:
                with suppress(Exception):
                    self._write_artifact(seat)
        if self.player_status_uri:
            status = {
                "schema_version": "1",
                "players": [
                    {
                        "slot": s.slot,
                        "state": "exited",
                        "exit_code": 0 if (s.technical and s.technical.eligible) else 1,
                        "reason": "Judged" if (s.technical and s.technical.eligible) else "Ineligible entry",
                        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                    for s in self.seats
                ],
            }
            with suppress(Exception):
                write_data(self.player_status_uri, json.dumps(status), content_type="application/json")
        replay_uri = os.environ.get("COGAME_SAVE_REPLAY_URI")
        if replay_uri:
            write_data(
                replay_uri,
                json.dumps(self.replay_payload(include_media=True), separators=(",", ":")),
                content_type="application/json",
                http_method=artifact_method("COGAME_SAVE_REPLAY_METHOD"),
            )
        results_uri = os.environ.get("COGAME_RESULTS_URI")
        if results_uri:
            write_data(
                results_uri,
                json.dumps(self.results, separators=(",", ":")),
                content_type="application/json",
                http_method=artifact_method("COGAME_RESULTS_METHOD"),
            )

    def _write_artifact(self, seat: Seat) -> None:
        assert seat.entry is not None
        path = self.tmp / f"artifact{seat.slot}.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("entry.json", seat.entry.meta.model_dump_json(by_alias=True, indent=2))
            archive.writestr("judge.json", json.dumps(seat.public(include_notes=True), indent=2))
            archive.writestr("video.mp4", self.media[seat.slot])
        write_data(seat.artifact_uri, path.read_bytes(), content_type="application/zip")

    # ------------------------------------------------------------------ live surfaces

    async def publish(self, event: dict[str, Any]) -> None:
        event = {**event, "t": round(time.time(), 3)}
        self.events.append(event)
        stale: list[WebSocket] = []
        for viewer in list(self.global_viewers):
            try:
                await viewer.send_json(event)
            except Exception:  # noqa: BLE001
                stale.append(viewer)
        for viewer in stale:
            self.global_viewers.discard(viewer)
        if event["type"] == "seat":
            slot = event["seat"]["slot"]
            for socket in list(self.player_sockets.get(slot, set())):
                with suppress(Exception):
                    await socket.send_json({"type": "observation", **event["seat"]})

    def snapshot(self, *, include_notes: bool) -> dict[str, Any]:
        return {
            "type": "snapshot",
            "phase": self.phase,
            "started": self.started,
            "done": self.done,
            "brief": self.config.brief if self.config else (self.replay or {}).get("brief", ""),
            "entries": [s.public(include_notes=include_notes) for s in self.seats],
            "results": self.results,
        }

    async def connect_global(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.global_viewers.add(websocket)
        try:
            await websocket.send_json(self.snapshot(include_notes=self.done))
            async for _ in websocket.iter_text():
                pass
        except Exception:  # noqa: BLE001
            pass
        finally:
            self.global_viewers.discard(websocket)

    def valid_token(self, slot: int, token: str) -> bool:
        return self.config is not None and 0 <= slot < len(self.config.tokens) and self.config.tokens[slot] == token

    async def connect_player(self, slot: int, token: str, websocket: WebSocket) -> None:
        if not self.valid_token(slot, token):
            await websocket.close(code=1008)
            return
        await websocket.accept()
        self.player_sockets.setdefault(slot, set()).add(websocket)
        try:
            seat = self.seats[slot]
            await websocket.send_json({"type": "observation", **seat.public(include_notes=self.done)})
            if self.done:
                await websocket.send_json({"type": "final", "slot": slot, "score": seat.score, "results": self.results})
            async for _ in websocket.iter_text():
                pass
        except Exception:  # noqa: BLE001
            pass
        finally:
            self.player_sockets.get(slot, set()).discard(websocket)

    async def _notify_players_final(self) -> None:
        for slot, sockets in self.player_sockets.items():
            for socket in list(sockets):
                with suppress(Exception):
                    await socket.send_json(
                        {"type": "final", "slot": slot, "score": self.seats[slot].score, "results": self.results}
                    )

    async def connect_replay(self, websocket: WebSocket) -> None:
        await websocket.accept()
        payload = self.replay if self.replay is not None else self.replay_payload(include_media=False)
        light = {k: v for k, v in payload.items() if k != "media"}
        await websocket.send_json({"type": "replay", **light})
        with suppress(Exception):
            async for _ in websocket.iter_text():
                await websocket.send_json({"type": "replay", **light})

    def replay_json(self) -> bytes:
        payload = self.replay if self.replay is not None else self.replay_payload(include_media=True)
        return json.dumps(payload, separators=(",", ":")).encode()

    def media_bytes(self, slot: int) -> bytes | None:
        if self.replay is not None:
            encoded = (self.replay.get("media") or {}).get(str(slot))
            return base64.b64decode(encoded) if encoded else None
        return self.media.get(slot)


def runtime_from_environment() -> Runtime:
    replay_uri = os.environ.get("COGAME_LOAD_REPLAY_URI")
    if replay_uri:
        return Runtime(None, replay=decode_replay_bytes(read_data(replay_uri)))
    config_uri = os.environ.get("COGAME_CONFIG_URI")
    if not config_uri:
        raise RuntimeError("COGAME_CONFIG_URI is required outside replay mode")
    config = GameConfig.model_validate_json(read_data(config_uri))
    seats_uri = os.environ.get("COGAME_PLAYER_SEATS_URI")
    seats_doc = json.loads(read_data(seats_uri)) if seats_uri else None
    if seats_doc is None:
        logger.warning("COGAME_PLAYER_SEATS_URI not set: every seat will be judged as missing")
    return Runtime(config, seats_doc=seats_doc)


def create_app(runtime: Runtime) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await runtime.startup()
        yield
        await runtime.shutdown()

    app = FastAPI(title="Softmax Video Marketing", lifespan=lifespan)
    jury_html = (STATIC_DIR / "jury.html").read_text(encoding="utf-8")
    player_html = (STATIC_DIR / "player.html").read_text(encoding="utf-8")

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"ok": True, "mode": "replay" if runtime.replay_mode else "episode", "phase": runtime.phase}

    @app.get("/client/player")
    def player_client(slot: int = -1, token: str = "") -> HTMLResponse:
        if not runtime.valid_token(slot, token):
            raise HTTPException(status_code=403, detail="invalid slot or token")
        return HTMLResponse(player_html)

    @app.get("/client/global")
    def global_client() -> HTMLResponse:
        return HTMLResponse(jury_html)

    @app.get("/client/replay")
    def replay_client() -> HTMLResponse:
        return HTMLResponse(jury_html)

    @app.get("/replay.json")
    def replay_json() -> Response:
        return Response(runtime.replay_json(), media_type="application/json")

    @app.get("/media/{slot}.mp4")
    def media(slot: int) -> Response:
        blob = runtime.media_bytes(slot)
        if blob is None:
            raise HTTPException(status_code=404, detail="no media for this seat")
        return Response(blob, media_type="video/mp4")

    @app.websocket("/player")
    async def player_socket(websocket: WebSocket) -> None:
        try:
            slot = int(websocket.query_params.get("slot", "-1"))
        except ValueError:
            slot = -1
        await runtime.connect_player(slot, websocket.query_params.get("token", ""), websocket)

    @app.websocket("/global")
    async def global_socket(websocket: WebSocket) -> None:
        await runtime.connect_global(websocket)

    @app.websocket("/replay")
    async def replay_socket(websocket: WebSocket) -> None:
        await runtime.connect_replay(websocket)

    return app


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    runtime = runtime_from_environment()
    app = create_app(runtime)
    host = os.environ.get("COGAME_HOST", "0.0.0.0")
    port = int(os.environ.get("COGAME_PORT", "8080"))
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning"))

    async def stop_server() -> None:
        await asyncio.sleep(0.5)
        server.should_exit = True

    runtime.on_complete = stop_server
    server.run()


if __name__ == "__main__":
    main()
