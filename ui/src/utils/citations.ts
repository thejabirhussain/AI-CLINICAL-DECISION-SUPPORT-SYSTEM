// The backend prompt asks the model to cite like "[Ref 1]" — also accept "[1]", "[1, 2]", "[Ref 1, 3]".
const CITE_RE = /\[(?:Refs?\.?\s*)?(\d+(?:\s*[,–-]\s*\d+)*)\]/gi;

/** Rewrites citation markers into markdown links (#cite-N) that the Markdown renderer turns into chips. */
export function linkCitations(markdown: string, sourceCount: number): string {
  if (!sourceCount) return markdown;
  return markdown.replace(CITE_RE, (match, nums: string, offset: number, full: string) => {
    // Skip things that are already markdown links: "[1](...)"
    if (full[offset + match.length] === '(') return match;
    const ids = nums
      .split(/\s*,\s*/)
      .map(n => parseInt(n, 10))
      .filter(n => n >= 1 && n <= sourceCount);
    if (!ids.length) return match;
    return ids.map(n => `[${n}](#cite-${n})`).join('');
  });
}

/** Removes emoji prefixes the backend prompt puts in section headers ("### 🧠 Clinical Interpretation"). */
export function stripHeaderEmoji(markdown: string): string {
  return markdown.replace(/^(#{1,6}\s*)[\p{Extended_Pictographic}️\s]+/gmu, '$1');
}

export const isWebUrl = (url: string) => /^https?:\/\//i.test(url);

/** Readable source label: the web host, or the dataset name for local:// knowledge-base entries. */
export function hostOf(url: string) {
  if (/^local:\/\/medquad/i.test(url)) return 'MedQuAD (NIH)';
  try {
    const u = new URL(url);
    return isWebUrl(url) ? u.hostname.replace(/^www\./, '') : u.hostname || url;
  } catch {
    return url;
  }
}
