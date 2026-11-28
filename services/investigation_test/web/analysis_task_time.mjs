// Display the server's observed durations; never replace missing time with the browser clock.
export const durationLabel = seconds => typeof seconds === 'number' && Number.isFinite(seconds) && seconds >= 0
  ? `${Number(seconds.toFixed(3))} 秒` : '未记录';

export function taskTimeRows(task, timeLabel) {
  return [['受理时间',timeLabel(task?.submitted_at)],['首次确认入队',timeLabel(task?.first_enqueued_at)],
    ['最近确认入队',timeLabel(task?.last_enqueued_at)],['首次开始执行',timeLabel(task?.started_at)],
    ['本地任务结束',timeLabel(task?.ended_at)],['服务观察时间',timeLabel(task?.observed_at)],
    ['总历时',durationLabel(task?.timing?.total_seconds)],['当前排队等待',durationLabel(task?.timing?.pending_queue_seconds)],
    ['当前重试等待（含排队）',durationLabel(task?.timing?.retry_wait_seconds)]];
}

export function attemptTimeRows(attempt, timeLabel) {
  return [['本次确认入队',timeLabel(attempt?.enqueued_at)],['本次开始',timeLabel(attempt?.started_at)],
    ['本地尝试结束',timeLabel(attempt?.local_ended_at)],['中断观察时间',timeLabel(attempt?.interruption_observed_at)],
    ['本次排队耗时',durationLabel(attempt?.timing?.queue_seconds)],
    ['本次执行耗时',durationLabel(attempt?.timing?.execution_seconds)]];
}

export function taskPhase(task) {
  const attempt=task?.attempts?.at(-1);
  if(task?.status==='skipped')return `任务已跳过：${task.reason_code??'原因未记录'}。`;
  if(task?.status==='accepted')return task.next_retry_at?'等待重试；预约时间不保证实际启动。':'已受理，等待执行。';
  if(task?.status==='running')return !attempt?.run_id?'准备阶段，尚无 Run/步骤记录。':
    task.active_step?`当前步骤：${task.active_step.name}`:'正在执行，尚无活动步骤记录。';
  if(attempt?.outcome==='unknown')return '本地已停止执行，远端结果仍未知；未推定 Run 已确定完成。';
  return '任务已本地收尾；分析交付及质量以实际 Run 结果为准。';
}

export function noRunLabel(task, attempt) {
  if(task?.status==='skipped' && attempt?.outcome==='completed' && attempt.local_state==='ended')
    return '检查已结束，任务已跳过，未创建 Run；不表示分析成功。';
  return attempt?.local_state==='running'?'正在准备，尚无关联 Run。':'此尝试未创建 Run，保留实际准备/错误记录。';
}

export function timingAnomalies(task, attempts=task?.attempts??[], step=task?.active_step) {
  return [...new Set([...(task?.timing?.anomalies??[]),...(step?.anomalies??[]),
    ...attempts.flatMap(a=>a.timing?.anomalies??[])])];
}
