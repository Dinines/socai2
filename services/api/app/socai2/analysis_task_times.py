"""Server-observed durations. Unknown or reversed timestamps never become zero."""


def seconds(start, end, field, anomalies):
    if start is None or end is None:
        return None
    value = (end - start).total_seconds()
    if value < 0:
        anomalies.append(field + "_negative")
        return None
    return value


def attempt_timing(attempt, observed_at):
    anomalies = []
    queue = seconds(attempt["enqueued_at"], attempt["started_at"], "queue_seconds", anomalies)
    end = observed_at if attempt["local_state"] == "running" else attempt["local_ended_at"]
    execution = seconds(attempt["started_at"], end, "execution_seconds", anomalies)
    return {"queue_seconds": queue, "execution_seconds": execution, "anomalies": anomalies}


def task_timing(original, root, attempts, observed_at):
    anomalies = []
    waiting = root["state"] in {"accepted", "waiting"}
    total = seconds(original["submitted_at"], root["ended_at"] or observed_at, "total_seconds", anomalies)
    pending = seconds(original["next_attempt_enqueued_at"], observed_at, "pending_queue_seconds", anomalies
        ) if waiting and not original["merged_into_task_id"] else None
    retry = seconds(attempts[-1]["local_ended_at"], observed_at, "retry_wait_seconds", anomalies
        ) if waiting and root["next_retry_at"] and attempts else None
    return {"total_seconds": total, "pending_queue_seconds": pending,
            "retry_wait_seconds": retry, "anomalies": anomalies}
