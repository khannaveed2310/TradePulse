"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Sidebar({ chats, currentChatId, setCurrentChatId, createNewChat, deleteChat }: any) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={`bg-gray-900 p-4 transition-all ${collapsed ? "w-16" : "w-64"}`}>
      <button onClick={() => setCollapsed(!collapsed)} className="mb-4 cursor-pointer">
        {collapsed ? <ChevronRight /> : <ChevronLeft />}
      </button>

      {!collapsed && (
        <>
          <button onClick={createNewChat} className="w-full bg-blue-600 p-2 rounded mb-4 cursor-pointer">
            + New Chat
          </button>

          <div className="space-y-2">
            {chats.map((chat: any) => (
              <div
                key={chat.id}
                className={`p-2 rounded flex justify-between cursor-pointer ${chat.id === currentChatId ? "bg-gray-700" : "bg-gray-800"}`}
              >
                <span onClick={() => setCurrentChatId(chat.id)}>{chat.title}</span>
                <button onClick={() => deleteChat(chat.id)} className="text-red-400 cursor-pointer">x</button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}