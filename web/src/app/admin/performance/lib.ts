// Shared date helper used by the assistant-stats view. The former per-metric
// analytics hooks here were removed with the legacy analytics endpoints; the
// admin analytics dashboard now lives in `performance/analytics/lib.ts`.

export function getDatesList(startDate: Date): string[] {
  const datesList: string[] = [];
  const endDate = new Date(); // current date

  for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
    const dateStr = d.toISOString().split("T")[0]; // 'YYYY-MM-DD'
    if (dateStr !== undefined) {
      datesList.push(dateStr);
    }
  }

  return datesList;
}
