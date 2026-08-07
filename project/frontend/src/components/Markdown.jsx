/* Minimal, dependency-free Markdown renderer for chat answers. Supports
   the subset of Markdown a lecture-chat answer realistically needs:
   paragraphs, line breaks, bold/italic/inline code, fenced code blocks,
   short headings, and bullet/numbered lists. Not a full CommonMark
   implementation -- just enough to make model answers readable without
   pulling in a markdown dependency. All text is escaped before any
   formatting is applied, so this never injects raw HTML. */

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderInline(text) {
  // Order matters: code spans first (so ** inside `code` isn't touched),
  // then bold, then italic.
  const escaped = escapeHtml(text);
  const regex = /`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*/g;
  const parts = [];
  let lastIndex = 0;
  let match;
  let key = 0;

  while ((match = regex.exec(escaped))) {
    if (match.index > lastIndex) parts.push(escaped.slice(lastIndex, match.index));
    if (match[1] !== undefined) {
      parts.push(
        <code className="md-inline-code" key={key++}>
          {match[1]}
        </code>
      );
    } else if (match[2] !== undefined) {
      parts.push(<strong key={key++}>{match[2]}</strong>);
    } else if (match[3] !== undefined) {
      parts.push(<em key={key++}>{match[3]}</em>);
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < escaped.length) parts.push(escaped.slice(lastIndex));
  return parts;
}

function renderBlock(block, key) {
  const lines = block.split("\n").filter((l) => l.length > 0);

  if (lines.length > 0 && lines.every((l) => /^\s*[-*]\s+/.test(l))) {
    return (
      <ul className="md-list" key={key}>
        {lines.map((l, i) => (
          <li key={i}>{renderInline(l.replace(/^\s*[-*]\s+/, ""))}</li>
        ))}
      </ul>
    );
  }

  if (lines.length > 0 && lines.every((l) => /^\s*\d+[.)]\s+/.test(l))) {
    return (
      <ol className="md-list" key={key}>
        {lines.map((l, i) => (
          <li key={i}>{renderInline(l.replace(/^\s*\d+[.)]\s+/, ""))}</li>
        ))}
      </ol>
    );
  }

  const headingMatch = block.match(/^(#{1,3})\s+(.*)$/);
  if (headingMatch) {
    const level = headingMatch[1].length;
    const Tag = level === 1 ? "h4" : level === 2 ? "h5" : "h6";
    return (
      <Tag className="md-heading" key={key}>
        {renderInline(headingMatch[2])}
      </Tag>
    );
  }

  return (
    <p className="md-paragraph" key={key}>
      {lines.map((l, i) => (
        <span key={i}>
          {renderInline(l)}
          {i < lines.length - 1 && <br />}
        </span>
      ))}
    </p>
  );
}

export default function Markdown({ text }) {
  if (!text) return null;

  // Pull fenced code blocks out first so their contents (which may
  // contain blank lines) don't get split apart by the paragraph splitter.
  const codeBlocks = [];
  const withPlaceholders = text.replace(/```(?:\w+)?\n([\s\S]*?)```/g, (_, code) => {
    codeBlocks.push(code.replace(/\n$/, ""));
    return `\u0000CODE_BLOCK_${codeBlocks.length - 1}\u0000`;
  });

  const blocks = withPlaceholders.split(/\n{2,}/).filter((b) => b.trim().length > 0);

  return (
    <div className="md-content">
      {blocks.map((block, i) => {
        const codeMatch = block.trim().match(/^\u0000CODE_BLOCK_(\d+)\u0000$/);
        if (codeMatch) {
          return (
            <pre className="md-code-block" key={i}>
              <code>{codeBlocks[Number(codeMatch[1])]}</code>
            </pre>
          );
        }
        return renderBlock(block, i);
      })}
    </div>
  );
}