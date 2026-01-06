import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/atom-one-dark.css';

/**
 * MessageRenderer Component
 * 
 * Renders markdown content with proper formatting
 * Supports:
 * - Headings (H1-H6)
 * - Bold/italic/strikethrough
 * - Code blocks with syntax highlighting
 * - Lists (ordered/unordered)
 * - Links
 * - Tables
 */

export interface MessageRendererProps {
  content: string;
  className?: string;
}

export const MessageRenderer: React.FC<MessageRendererProps> = ({
  content,
  className = '',
}) => {
  return (
    <div className={`prose prose-invert max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // Headings
          h1: ({ node, ...props }) => (
            <h1 className="text-2xl font-bold text-zinc-100 mt-4 mb-2" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-xl font-bold text-zinc-100 mt-3 mb-2" {...props} />
          ),
          h3: ({ node, ...props }) => (
            <h3 className="text-lg font-bold text-zinc-100 mt-3 mb-1.5" {...props} />
          ),
          h4: ({ node, ...props }) => (
            <h4 className="text-base font-bold text-zinc-100 mt-2 mb-1" {...props} />
          ),
          h5: ({ node, ...props }) => (
            <h5 className="font-bold text-zinc-100 mt-2 mb-1" {...props} />
          ),
          h6: ({ node, ...props }) => (
            <h6 className="font-bold text-zinc-300 mt-2 mb-1" {...props} />
          ),

          // Paragraphs
          p: ({ node, ...props }) => (
            <p className="text-zinc-200 leading-relaxed mb-3" {...props} />
          ),

          // Lists
          ul: ({ node, ...props }) => (
            <ul className="list-disc list-inside text-zinc-200 mb-3 space-y-1" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="list-decimal list-inside text-zinc-200 mb-3 space-y-1" {...props} />
          ),
          li: ({ node, ...props }) => (
            <li className="text-zinc-200" {...props} />
          ),

          // Code
          code: ({ node, inline, className, ...props }: any) => {
            if (inline) {
              return (
                <code className="bg-zinc-800 text-zinc-100 px-1.5 py-0.5 rounded text-sm font-mono" {...props} />
              );
            }
            return (
              <code className="block bg-zinc-900 text-zinc-100 p-3 rounded-lg overflow-x-auto mb-3 font-mono text-sm" {...props} />
            );
          },
          pre: ({ node, ...props }) => (
            <pre className="bg-zinc-900 p-3 rounded-lg overflow-x-auto mb-3" {...props} />
          ),

          // Links
          a: ({ node, ...props }) => (
            <a className="text-blue-400 hover:text-blue-300 underline" {...props} />
          ),

          // Blockquotes
          blockquote: ({ node, ...props }) => (
            <blockquote className="border-l-4 border-zinc-600 pl-4 py-2 text-zinc-300 italic mb-3" {...props} />
          ),

          // Tables
          table: ({ node, ...props }) => (
            <table className="w-full border-collapse mb-3" {...props} />
          ),
          thead: ({ node, ...props }) => (
            <thead className="bg-zinc-800" {...props} />
          ),
          tbody: ({ node, ...props }) => (
            <tbody {...props} />
          ),
          tr: ({ node, ...props }) => (
            <tr className="border-b border-zinc-700" {...props} />
          ),
          th: ({ node, ...props }) => (
            <th className="text-left px-3 py-2 text-zinc-100 font-semibold" {...props} />
          ),
          td: ({ node, ...props }) => (
            <td className="px-3 py-2 text-zinc-200" {...props} />
          ),

          // Horizontal rule
          hr: ({ node, ...props }) => (
            <hr className="border-zinc-700 my-4" {...props} />
          ),

          // Strong/emphasis
          strong: ({ node, ...props }) => (
            <strong className="font-bold text-zinc-100" {...props} />
          ),
          em: ({ node, ...props }) => (
            <em className="italic text-zinc-200" {...props} />
          ),

          // Strikethrough
          del: ({ node, ...props }) => (
            <del className="line-through text-zinc-400" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MessageRenderer;
