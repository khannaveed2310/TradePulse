"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Message from "./Message";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function ChatBox({ currentChat, setCurrentChat }: any) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentChat]);

  const appendBotMessage = (text: string, extras: Record<string, any> = {}) => {
    setCurrentChat((prev: any) => ({
      ...prev,
      messages: [...(prev.messages || []), { role: "bot", text, ...extras }],
    }));
  };

  const sendMessage = async () => {
    if (!input.trim() || !currentChat) return;
    const userText = input.trim();

    setCurrentChat((prev: any) => ({
      ...prev,
      messages: [...(prev.messages || []), { role: "user", text: userText }],
    }));
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      handleBotResponse(data, userText);
    } catch (err) {
      console.error(err);
      appendBotMessage("❌ Error contacting server. Please try again.");
      setLoading(false);
    }
  };

  const handleSelect = async (country: string, originalMessage: string) => {
    setLoading(true);

    setCurrentChat((prev: any) => ({
      ...prev,
      messages: [
        ...(prev.messages || []),
        { role: "user", text: `Selected: ${country}` },
      ],
    }));

    try {
      const res = await fetch(`${API_BASE}/api/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: originalMessage,
          selected_country: country,
        }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      handleBotResponse(data, originalMessage);
    } catch (err) {
      console.error(err);
      appendBotMessage("❌ Error fetching data. Please try again.");
      setLoading(false);
    }
  };

  const handleBotResponse = (data: any, originalMessage: string) => {
    setCurrentChat((prev: any) => ({
      ...prev,
      messages: [
        ...(prev.messages || []),
        {
          role: "bot",
          text: data.message || "Done",
          file_url: data.file_url || null,
          source: data.source || null,
          options: data.options || null,
          originalMessage,
        },
      ],
    }));

    if (data.source === "processing") {
      startPolling(originalMessage);
    } else {
      setLoading(false);
    }
  };

  const startPolling = (originalMessage: string) => {
    const lower = originalMessage.toLowerCase();
    const data_type = lower.includes("import") ? "import" : "export";
    const yearMatch = lower.match(/\b(20\d{2})\b/);
    const year = yearMatch ? yearMatch[1] : "";

    const skipWords = new Set([
      "show",
      "me",
      "i",
      "need",
      "want",
      "get",
      "fetch",
      "find",
      "import",
      "export",
      "data",
      "for",
      "of",
      "in",
      "the",
      "from",
      "trade",
      "year",
      "please",
      "give",
    ]);

    const country = lower
      .replace(/[^\w\s]/g, "")
      .split(" ")
      .filter((w: string) => !skipWords.has(w) && !/^\d+$/.test(w))
      .join(" ")
      .replace(/\b\w/g, (c: string) => c.toUpperCase())
      .trim();

    if (!year || !country) {
      setLoading(false);
      return;
    }

    if (pollingRef.current) clearInterval(pollingRef.current);

    pollingRef.current = setInterval(async () => {
      try {
        const params = new URLSearchParams({ country, year, data_type });
        const res = await fetch(`${API_BASE}/api/status/?${params}`);
        const result = await res.json();

        console.log("Poll result:", result);

        if (result.source === "db") {
          clearInterval(pollingRef.current!);
          pollingRef.current = null;
          // Use functional update — no stale closure issue
          setCurrentChat((prev: any) => ({
            ...prev,
            messages: [
              ...(prev.messages || []),
              {
                role: "bot",
                text: result.message,
                file_url: result.file_url,
                source: "db",
              },
            ],
          }));
          setLoading(false);
        } else if (
          result.source === "failed" ||
          result.source === "not_found"
        ) {
          clearInterval(pollingRef.current!);
          pollingRef.current = null;
          setCurrentChat((prev: any) => ({
            ...prev,
            messages: [
              ...(prev.messages || []),
              {
                role: "bot",
                text: result.message || "❌ Failed to fetch data.",
                source: "failed",
              },
            ],
          }));
          setLoading(false);
        }
        // source === "processing" → keep polling
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 5000);
  };

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {(currentChat?.messages || [])
          .filter((msg: any, i: number, arr: any[]) => {
            if (msg.role === "bot" && msg.source === "processing") {
              return !arr.slice(i + 1).some((m: any) => m.source === "db");
            }
            return true;
          })
          .map((msg: any, i: number) => (
            <Message
              key={i}
              msg={msg}
              onSelect={(country: string) =>
                handleSelect(country, msg.originalMessage || "")
              }
            />
          ))}

        <div ref={bottomRef} />
      </div>

      <div className="border-t border-gray-800 p-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !loading && sendMessage()}
          disabled={loading}
          placeholder='e.g. "Show me export data for India 2025"'
          className="flex-1 bg-gray-900 border border-gray-700 rounded-xl p-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="bg-blue-600 px-5 rounded-xl cursor-pointer hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
