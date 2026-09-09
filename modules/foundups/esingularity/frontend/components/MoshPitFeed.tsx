import type { Activity, Projection } from '@/lib/mosh-pit-policy';

function Notes({ activity }: { activity: Activity }) {
  return <>{activity.details.map((detail, index) => <p key={index}>{detail}</p>)}
    {activity.truth === 'OBSERVED' && <small>記録あり</small>}
    {activity.truth === 'REPORTED_BY_012' && <small>012からの報告</small>}
    {activity.truth === 'INFERRED' && <small>推定</small>}
    {activity.truth === 'PROPOSED' && <small>提案</small>}
  </>;
}

function dayLabel(date: string | null) {
  if (!date) return '日付未確認';
  return new Intl.DateTimeFormat('ja-JP', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short', timeZone: 'Asia/Tokyo' }).format(new Date(`${date}T12:00:00+09:00`));
}

export default function MoshPitFeed({ projection }: { projection: Projection }) {
  if (!projection.days.length) return <p className="mosh-status">共有された活動はまだありません。</p>;
  return <div className="mosh-days">{projection.days.map(day =>
    <section key={day.date ?? 'undated'} aria-label={dayLabel(day.date)}>
      <h2><time dateTime={day.date ?? undefined}>{dayLabel(day.date)}</time></h2>
      <ul className="mosh-activities">{day.entries.map(entry => <li key={entry.event_id}>
        <details><summary><span>{entry.summary}</span><small>{entry.actor}</small></summary>
          <div className="mosh-thread"><Notes activity={entry} />
            {entry.replies.length > 0 && <><h3>この活動の会話</h3><ol>{entry.replies.map(reply => <li key={reply.event_id}>
              <p><strong>{reply.actor}</strong> · {reply.summary}</p><Notes activity={reply} />
            </li>)}</ol></>}
            {entry.more_replies && <p>ほかにも返信があります。この表示では最初の50件まで確認できます。</p>}
            {!entry.details.length && !entry.replies.length && <p>追加の詳細はまだありません。</p>}
          </div>
        </details>
      </li>)}</ul>
    </section>)}
    {projection.has_more && <p className="mosh-status">過去の活動はこの表示に含まれていません。現在は最新の50件まで確認できます。</p>}
  </div>;
}
