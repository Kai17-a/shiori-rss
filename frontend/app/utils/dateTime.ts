const pad = (value: number) => String(value).padStart(2, "0");

export const formatDateTime = (value: string | null | undefined) => {
  if (!value) {
    return "";
  }

  const sourceDateTime = value.match(
    /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/,
  );
  if (sourceDateTime) {
    const [, year, month, day, hour, minute, second = "00"] = sourceDateTime;
    return `${year}/${month}/${day} ${hour}:${minute}:${second}`;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return [
    date.getFullYear(),
    "/",
    pad(date.getMonth() + 1),
    "/",
    pad(date.getDate()),
    " ",
    pad(date.getHours()),
    ":",
    pad(date.getMinutes()),
    ":",
    pad(date.getSeconds()),
  ].join("");
};
