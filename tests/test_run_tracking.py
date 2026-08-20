from jobsearcher.db.repository import (
    start_run,
    finish_run,
    fail_run,
    get_run,
    list_recent_runs,
)


def test_start_run_creates_running_row(conn):
    run_id = start_run(conn)
    run = get_run(conn, run_id)
    assert run.status == "running"
    assert run.started_at != ""
    assert run.finished_at is None


def test_finish_run_records_stats_and_completed_status(conn):
    run_id = start_run(conn)
    stats = {"ingested": 3, "matched": 1, "notified": 1}
    finish_run(conn, run_id, stats)

    run = get_run(conn, run_id)
    assert run.status == "completed"
    assert run.stats == stats
    assert run.finished_at is not None


def test_fail_run_records_error_and_failed_status(conn):
    run_id = start_run(conn)
    fail_run(conn, run_id, "Playwright crashed: timeout")

    run = get_run(conn, run_id)
    assert run.status == "failed"
    assert run.error_message == "Playwright crashed: timeout"
    assert run.finished_at is not None


def test_list_recent_runs_returns_newest_first(conn):
    first = start_run(conn)
    finish_run(conn, first, {"ingested": 0})
    second = start_run(conn)
    finish_run(conn, second, {"ingested": 5})

    runs = list_recent_runs(conn, limit=10)
    assert [r.id for r in runs] == [second, first]


def test_list_recent_runs_respects_limit(conn):
    for _ in range(5):
        run_id = start_run(conn)
        finish_run(conn, run_id, {})

    runs = list_recent_runs(conn, limit=2)
    assert len(runs) == 2
