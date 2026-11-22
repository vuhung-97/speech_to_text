import { describe, expect, it } from "vitest";

import { dayLabel, filterSessions, groupSessions, when } from "./sessionList";

const now = new Date();
const at = (offsetDays) =>
  new Date(now.getFullYear(), now.getMonth(), now.getDate() - offsetDays, 10, 30)
    .getTime() / 1000;

describe("sessionList", () => {
  it("labels today, yesterday and older days", () => {
    expect(dayLabel(at(0))).toBe("Hôm nay");
    expect(dayLabel(at(1))).toBe("Hôm qua");
    expect(dayLabel(at(9))).toBe("Trước đó");
    expect(dayLabel(0)).toBe("Trước đó");
  });

  it("groups sessions in the order they first appear", () => {
    const groups = groupSessions([
      { id: "a", updated_at: at(0) },
      { id: "b", updated_at: at(0) },
      { id: "c", updated_at: at(3) },
    ]);

    expect(groups.map((group) => group.label)).toEqual(["Hôm nay", "Trước đó"]);
    expect(groups[0].items.map((item) => item.id)).toEqual(["a", "b"]);
  });

  it("matches question, title and id case-insensitively", () => {
    const items = [
      { id: "s1", first_question: "Quy trình đăng ký", title: "" },
      { id: "s2", first_question: "", title: "Kế hoạch" },
      { id: "s3", first_question: "", title: "" },
    ];

    expect(filterSessions(items, "QUY").map((item) => item.id)).toEqual(["s1"]);
    expect(filterSessions(items, "kế").map((item) => item.id)).toEqual(["s2"]);
    expect(filterSessions(items, "s3").map((item) => item.id)).toEqual(["s3"]);
    expect(filterSessions(items, "  ")).toBe(items);
  });

  it("formats the clock time and tolerates missing values", () => {
    expect(when(0)).toBe("");
    expect(when(at(0))).toMatch(/\d{2}:\d{2}/);
  });
});
