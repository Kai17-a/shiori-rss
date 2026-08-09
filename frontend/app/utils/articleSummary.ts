export const ARTICLE_SUMMARY_MAX_LENGTH = 160;

const decodeHtmlEntities = (value: string) =>
  value.replace(/&(#x?[0-9a-f]+|amp|apos|gt|lt|nbsp|quot);/gi, (entity, token: string) => {
    const normalized = token.toLowerCase();
    const namedEntities: Record<string, string> = {
      amp: "&",
      apos: "'",
      gt: ">",
      lt: "<",
      nbsp: " ",
      quot: '"',
    };
    const namedEntity = namedEntities[normalized];
    if (namedEntity !== undefined) {
      return namedEntity;
    }

    const radix = normalized.startsWith("#x") ? 16 : 10;
    const codePoint = Number.parseInt(normalized.slice(radix === 16 ? 2 : 1), radix);
    return Number.isNaN(codePoint) || codePoint > 0x10ffff
      ? entity
      : String.fromCodePoint(codePoint);
  });

export const formatArticleSummary = (
  value: string | null | undefined,
  maxLength = ARTICLE_SUMMARY_MAX_LENGTH,
) => {
  if (!value) {
    return "";
  }

  const plainText = decodeHtmlEntities(value.replace(/<[^>]*>/g, " "))
    .replace(/\s+/g, " ")
    .trim();
  const characters = Array.from(plainText);
  if (characters.length <= maxLength) {
    return plainText;
  }
  return `${characters.slice(0, maxLength).join("").trimEnd()}…`;
};
