"""HTTP routes with the upstream SQL-aware ledger fixture, no real database."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'services/api/tests'))
import test_investigation_replay as fixture


def rows(sequences):
    result = []
    for seq in sequences:
        event = fixture._event(abs(seq))
        event.seq = seq
        event.kind = 'triage_started' if seq == -1 else 'triage_verdict'
        result.append(event)
    return result


@pytest.mark.parametrize('sequences', [(-1,), (-1, 1)])
def test_returned_started_cursor_can_be_used_without_overlap(sequences):
    session = fixture._Session(run=fixture._run(), events=rows(sequences))
    with fixture._client(session) as client:
        first = client.get(fixture._EVENTS, params={'limit': 1})
        assert first.status_code == 200 and first.json()['next_seq'] == -1
        second = client.get(fixture._EVENTS, params={'since': first.json()['next_seq']})
        assert second.status_code == 200
        assert [item['seq'] for item in second.json()['items']] == [seq for seq in sequences if seq > -1]
        assert second.json()['total'] == len(sequences) - 1


@pytest.mark.parametrize('cursor,status,sequences', [(-2, 422, []), (-1, 200, [1, 3]), (0, 200, [1, 3]), (1, 200, [3])])
def test_cursor_boundary_preserves_nonnegative_semantics(cursor, status, sequences):
    session = fixture._Session(run=fixture._run(), events=rows((3, -1, 1)))
    with fixture._client(session) as client:
        response = client.get(fixture._EVENTS, params={'since': cursor})
        assert response.status_code == status
        if status == 200:
            assert [item['seq'] for item in response.json()['items']] == sequences


def test_negative_cursor_still_requires_cases_read():
    session = fixture._Session(run=fixture._run(), events=rows((-1,)))
    with fixture._client(session, user=fixture._user(scopes=['alerts:read'])) as client:
        assert client.get(fixture._EVENTS, params={'since': -1}).status_code == 403


def test_negative_cursor_preserves_unknown_run_404():
    with fixture._client(fixture._Session(run=None)) as client:
        assert client.get(fixture._EVENTS, params={'since': -1}).status_code == 404
