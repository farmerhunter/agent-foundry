#!/usr/bin/env python3
"""Static AF18 LearningSignal validation and in-memory opaque index projection."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import secrets
import sys
from urllib.parse import unquote
from pathlib import Path
from typing import Any


IDENTITY_ALGORITHM = "af18-learning-signal-identity-v1"
CURSOR_VERSION = "af18-learning-signal-cursor-v1"
KEY_PREFIX = "af18-ls-v1-"
REFERENCE_PREFIX = "af18-ls-ref-v1-"
CURSOR_PREFIX = "af18-ls-cur-v1-"
REQUIRED_FIELDS = {
    "candidate_key", "state", "source_work_anchor", "source_role", "lesson_type",
    "summary", "applicability", "evidence_anchors", "residual_limits",
    "privacy_status", "explicit_exclusions",
}
FORBIDDEN_MARKERS = (
    "selected-vault", "vault/", "practice_id", "asset_id", "publish", "activation",
    "harvester", "#426", "formal harvest", "prompt", "transcript", "tool history",
    "raw model", "raw content", "secret", "native id", "identity linkage",
)
FORBIDDEN_REFERENCE_MARKERS = (
    "selected-vault", "selected_vault", "vault/private", "/private/", "native-id",
    "native_id", "native%2did", "native%5fid", "content=", "/content/", "raw-content",
    "raw_content", "transcript", "prompt", "secret",
)
MAX_REFERENCE_NORMALIZATION_ROUNDS = 4


class CandidateError(ValueError):
    pass


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def is_opaque_ascii(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value.isascii() and all(32 <= ord(char) < 127 for char in value)


def canonical_anchors(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise CandidateError("held_candidate_invalid")
    if any(not isinstance(anchor, str) or not anchor or not anchor.startswith("https://") or not is_safe_reference(anchor) for anchor in value):
        raise CandidateError("held_candidate_invalid")
    normalized = sorted(value)
    if len(set(normalized)) != len(normalized):
        raise CandidateError("held_candidate_invalid")
    return normalized


def is_safe_reference(value: str) -> bool:
    normalized = value
    try:
        for _ in range(MAX_REFERENCE_NORMALIZATION_ROUNDS):
            decoded = unquote(normalized, errors="strict")
            if decoded == normalized:
                if "%" in normalized or not normalized.isascii():
                    return False
                marker_value = re.sub(r"[\\\\/]+", "/", normalized).lower()
                if marker_value in {".", ".."} or re.search(r"/(?:\.{1,2})(?:[/?#]|$)", marker_value):
                    return False
                return not any(marker in marker_value for marker in FORBIDDEN_REFERENCE_MARKERS)
            normalized = decoded
    except UnicodeDecodeError:
        return False
    return False


def candidate_key(source_work_identity: str, evidence_anchors: list[str]) -> str:
    payload = {
        "identity_algorithm": IDENTITY_ALGORITHM,
        "source_work_identity": source_work_identity,
        "evidence_anchors": evidence_anchors,
    }
    return KEY_PREFIX + hashlib.sha256(canonical_json(payload)).hexdigest()


def has_forbidden_content(record: dict[str, Any]) -> bool:
    values = (record[key] for key in ("source_role", "lesson_type", "summary", "applicability"))
    return any(marker in value.lower() for value in values if isinstance(value, str) for marker in FORBIDDEN_MARKERS)


def validate_candidate(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != REQUIRED_FIELDS:
        raise CandidateError("held_candidate_invalid")
    if record.get("state") != "candidate_hold" or record.get("privacy_status") != "pass_metadata_only":
        raise CandidateError("held_candidate_invalid")
    if not is_opaque_ascii(record.get("source_work_anchor")):
        raise CandidateError("held_candidate_invalid")
    if not is_safe_reference(record["source_work_anchor"]):
        raise CandidateError("held_candidate_invalid")
    anchors = canonical_anchors(record.get("evidence_anchors"))
    if any(not isinstance(record[name], str) or not record[name].strip() for name in REQUIRED_FIELDS - {"evidence_anchors"}):
        raise CandidateError("held_candidate_invalid")
    if has_forbidden_content(record):
        raise CandidateError("held_candidate_invalid")
    if not hmac.compare_digest(record["candidate_key"], candidate_key(record["source_work_anchor"], anchors)):
        raise CandidateError("held_candidate_invalid")
    return record


def opaque_reference(key: str) -> str:
    return REFERENCE_PREFIX + hashlib.sha256(key.encode("ascii")).hexdigest()


class LearningSignalIndex:
    """A process-local index; instances intentionally cannot resume each other."""

    def __init__(self, records: Any) -> None:
        if not isinstance(records, list):
            raise CandidateError("held_candidate_invalid")
        validated = [validate_candidate(record) for record in records]
        keys = [record["candidate_key"] for record in validated]
        if len(keys) != len(set(keys)):
            raise CandidateError("held_duplicate_candidate")
        self._records = sorted(validated, key=lambda record: record["candidate_key"])
        self._references = [opaque_reference(record["candidate_key"]) for record in self._records]
        self._batch_fingerprint = hashlib.sha256(canonical_json({"identity_algorithm": IDENTITY_ALGORITHM, "candidate_keys": [record["candidate_key"] for record in self._records]})).hexdigest()
        self._secret = secrets.token_bytes(32)
        self._cursors: dict[str, tuple[bytes, str]] = {}

    @staticmethod
    def _valid_page_size(page_size: Any) -> bool:
        return isinstance(page_size, int) and not isinstance(page_size, bool) and 1 <= page_size <= 25

    def _cursor_payload(self, page_size: int, last_reference: str) -> bytes:
        return canonical_json({
            "cursor_version": CURSOR_VERSION,
            "batch_fingerprint": self._batch_fingerprint,
            "identity_algorithm": IDENTITY_ALGORITHM,
            "page_size": page_size,
            "last_ordered_reference": last_reference,
        })

    def _issue_cursor(self, page_size: int, last_reference: str) -> str:
        payload = self._cursor_payload(page_size, last_reference)
        tag = hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
        nonce = secrets.token_urlsafe(18)
        token = f"{CURSOR_PREFIX}{nonce}.{tag}"
        self._cursors[token] = (payload, tag)
        return token

    def _read_cursor(self, cursor: Any, page_size: Any) -> int | None:
        if not self._valid_page_size(page_size) or not isinstance(cursor, str):
            return None
        stored = self._cursors.get(cursor)
        if stored is None or not cursor.startswith(CURSOR_PREFIX) or cursor.count(".") != 1:
            return None
        payload, stored_tag = stored
        given_tag = cursor.rsplit(".", 1)[1]
        expected_tag = hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(given_tag, stored_tag) or not hmac.compare_digest(stored_tag, expected_tag):
            return None
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return None
        if decoded != {
            "cursor_version": CURSOR_VERSION,
            "batch_fingerprint": self._batch_fingerprint,
            "identity_algorithm": IDENTITY_ALGORITHM,
            "page_size": page_size,
            "last_ordered_reference": decoded.get("last_ordered_reference"),
        }:
            return None
        last = decoded["last_ordered_reference"]
        if last == "":
            return 0
        if last not in self._references:
            return None
        return self._references.index(last) + 1

    def default_projection(self, page_size: Any = 25) -> dict[str, Any]:
        if not self._valid_page_size(page_size):
            return {"routing_state": "held_cursor_invalid"}
        cursor = self._issue_cursor(page_size, "") if self._references else None
        return {"count": len(self._references), "routing_state": "candidate_hold", "next_cursor": cursor}

    def page(self, cursor: Any, page_size: Any) -> dict[str, Any]:
        start = self._read_cursor(cursor, page_size)
        if start is None:
            return {"routing_state": "held_cursor_invalid"}
        references = self._references[start:start + page_size]
        next_cursor = self._issue_cursor(page_size, references[-1]) if start + page_size < len(self._references) else None
        return {"references": references, "next_cursor": next_cursor}


def hold_from(error: CandidateError) -> dict[str, str]:
    return {"routing_state": str(error)}


def load_batch(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CandidateError("held_candidate_invalid") from error


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate static LearningSignal records and render an in-memory opaque index projection.")
    parser.add_argument("--batch-json", type=Path, required=True)
    parser.add_argument("--mode", choices=("default", "page"), default="default")
    parser.add_argument("--cursor")
    parser.add_argument("--page-size", type=int)
    args = parser.parse_args()
    try:
        index = LearningSignalIndex(load_batch(args.batch_json))
        if args.mode == "default":
            output: dict[str, Any] = index.default_projection(args.page_size if args.page_size is not None else 25)
        else:
            output = index.page(args.cursor, args.page_size)
        print(json.dumps(output, sort_keys=True))
        return 0
    except CandidateError as error:
        print(json.dumps(hold_from(error), sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
