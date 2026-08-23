export type PaginationItem =
  | { type: "page"; label: string; value: number }
  | { type: "ellipsis" };

export const buildPaginationItems = (current: number, total: number): PaginationItem[] => {
  if (total <= 5) {
    return Array.from({ length: total }, (_, index) => ({
      type: "page" as const,
      label: String(index + 1),
      value: index + 1,
    }));
  }

  const pages = new Set<number>([1, total, current]);
  if (current > 1) pages.add(current - 1);
  if (current < total) pages.add(current + 1);

  return Array.from(pages)
    .sort((left, right) => left - right)
    .reduce<PaginationItem[]>((items, value, index, values) => {
      items.push({ type: "page", label: String(value), value });
      const next = values[index + 1];
      if (next && next - value > 1) items.push({ type: "ellipsis" });
      return items;
    }, []);
};
