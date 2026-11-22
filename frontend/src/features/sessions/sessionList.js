// Pure helpers for the session history screen: dates, grouping and search.

const MS_PER_DAY = 86_400_000;

export function when(value) {
  if (!value) return "";
  try {
    return new Date(value * 1000).toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export function dayLabel(value) {
  if (!value) return "Trước đó";
  const date = new Date(value * 1000);
  if (Number.isNaN(date.getTime())) return "Trước đó";
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const days = Math.round((start - target) / MS_PER_DAY);
  if (days === 0) return "Hôm nay";
  if (days === 1) return "Hôm qua";
  return "Trước đó";
}

export function groupSessions(items) {
  const groups = [];
  for (const item of items) {
    const label = dayLabel(item.updated_at);
    let group = groups.find((entry) => entry.label === label);
    if (!group) {
      group = { label, items: [] };
      groups.push(group);
    }
    group.items.push(item);
  }
  return groups;
}

export function filterSessions(items, query) {
  const needle = query.trim().toLowerCase();
  if (!needle) return items;
  return items.filter((item) =>
    [item.first_question, item.title, item.id]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(needle)),
  );
}
