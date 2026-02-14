import React, { useState } from "react";
import { Copy, Check, Download } from "lucide-react";

const CodeBlock = ({ 
  code, 
  language = "bash", 
  filename,
  showCopy = true,
  showDownload = true,
  onDownload,
  className = ""
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const handleDownload = () => {
    if (onDownload) {
      onDownload();
    } else if (filename) {
      const blob = new Blob([code], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  // Simple syntax highlighting for common languages
  const highlightCode = (code, lang) => {
    if (lang === "bash" || lang === "sh") {
      return code
        .replace(/^#!/gm, '<span class="text-purple-400">#!/</span>')
        .replace(/^#.*$/gm, '<span class="text-slate-500">$&</span>')
        .replace(/(\$[a-zA-Z_][a-zA-Z0-9_]*)/g, '<span class="text-blue-400">$1</span>')
        .replace(/(["'][^"']*["'])/g, '<span class="text-green-400">$1</span>')
        .replace(/\b(if|then|else|fi|for|do|done|while|case|esac|function|return)\b/g, '<span class="text-pink-400">$1</span>');
    } else if (lang === "python" || lang === "py") {
      return code
        .replace(/^#.*$/gm, '<span class="text-slate-500">$&</span>')
        .replace(/("""[\s\S]*?""")/g, '<span class="text-slate-500">$1</span>')
        .replace(/("""[\s\S]*?""")/g, '<span class="text-slate-500">$1</span>')
        .replace(/(["'][^"']*["'])/g, '<span class="text-green-400">$1</span>')
        .replace(/\b(def|class|import|from|if|elif|else|for|while|try|except|finally|return|with|as|pass|break|continue)\b/g, '<span class="text-pink-400">$1</span>')
        .replace(/\b(True|False|None)\b/g, '<span class="text-blue-400">$1</span>');
    }
    return code;
  };

  return (
    <div className={`relative rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-900 dark:bg-slate-950 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 dark:bg-slate-900 border-b border-slate-700 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wide">
            {language}
          </span>
          {filename && (
            <span className="text-xs text-slate-500 font-mono">{filename}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {showCopy && (
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded transition-colors"
              title="Copy to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy</span>
                </>
              )}
            </button>
          )}
          {showDownload && (onDownload || filename) && (
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded transition-colors"
              title="Download file"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download</span>
            </button>
          )}
        </div>
      </div>
      
      {/* Code Content */}
      <div className="overflow-x-auto">
        <pre className="p-4 m-0 text-sm font-mono leading-relaxed text-slate-100">
          <code
            dangerouslySetInnerHTML={{
              __html: highlightCode(code, language),
            }}
          />
        </pre>
      </div>
    </div>
  );
};

export default CodeBlock;
