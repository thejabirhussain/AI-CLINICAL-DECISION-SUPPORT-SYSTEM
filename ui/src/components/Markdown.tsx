import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Source } from '../types';
import { linkCitations, stripHeaderEmoji } from '../utils/citations';

interface Props {
  content: string;
  sources?: Source[];
  onCite?: (index: number) => void;
  className?: string;
}

export function Markdown({ content, sources = [], onCite, className = 'doc' }: Props) {
  const md = linkCitations(stripHeaderEmoji(content), sources.length);

  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            const m = href?.match(/^#cite-(\d+)$/);
            if (m) {
              const n = parseInt(m[1], 10);
              const src = sources[n - 1];
              return (
                <sup className="mx-[1px]">
                  <button
                    type="button"
                    onClick={() => onCite?.(n)}
                    title={src?.title}
                    className="text-[11px] font-medium text-brand hover:underline cursor-pointer"
                  >
                    [{n}]
                  </button>
                </sup>
              );
            }
            return (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {md}
      </ReactMarkdown>
    </div>
  );
}
