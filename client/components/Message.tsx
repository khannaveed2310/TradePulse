export default function Message({ msg, onSelect }: any) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`p-4 rounded-2xl max-w-[75%] space-y-3 ${isUser ? "bg-blue-700 text-white" : "bg-gray-800 text-white"}`}>
        <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>

        {msg.options && msg.options.length > 0 && (
          <div className="space-y-1.5">
            {msg.options.map((opt: string, i: number) => (
              <button key={i} onClick={() => onSelect(opt)} className="block w-full text-left bg-gray-700 hover:bg-gray-600 px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer">
                {opt}
              </button>
            ))}
          </div>
        )}

        {msg.file_url && (
          <a href={msg.file_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors w-fit">
            📥 Download {msg.text?.toLowerCase().includes("import") ? "Import" : "Export"} File
          </a>
        )}

        {msg.source && msg.source !== "error" && (
          <p className="text-xs text-gray-400">
            Source: <span className={msg.source === "db" ? "text-green-400" : msg.source === "processing" ? "text-yellow-400" : msg.source === "failed" ? "text-red-400" : "text-gray-400"}>{msg.source}</span>
          </p>
        )}
      </div>
    </div>
  );
}