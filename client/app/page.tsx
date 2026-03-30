"use client";

import { useState } from "react";
import ChatBox from "@/components/ChatBox";
import Sidebar from "@/components/Sidebar";

export default function Home() {
  const [chats, setChats] = useState([
    { id: 1, title: "New Chat", messages: [] },
  ]);
  const [currentChatId, setCurrentChatId] = useState(1);

  const currentChat = chats.find((c) => c.id === currentChatId);

  const createNewChat = () => {
    const newChat = { id: Date.now(), title: "New Chat", messages: [] };
    setChats((prev) => [newChat, ...prev]);
    setCurrentChatId(newChat.id);
  };

  const deleteChat = (id: number) => {
    setChats((prev) => {
      const filtered = prev.filter((c) => c.id !== id);
      if (id === currentChatId && filtered.length > 0) {
        setCurrentChatId(filtered[0].id);
      }
      return filtered;
    });
  };

  // This updater is passed to ChatBox — supports both object and functional updates
  const updateCurrentChat = (updater: any) => {
    setChats((prevChats) => {
      return prevChats.map((chat) => {
        if (chat.id !== currentChatId) return chat;
        // If updater is a function, call it with current chat
        if (typeof updater === "function") {
          return updater(chat);
        }
        // If updater is an object, merge it
        return updater;
      });
    });
  };

  return (
    <div className="flex h-screen bg-black text-white">
      <Sidebar
        chats={chats}
        currentChatId={currentChatId}
        setCurrentChatId={setCurrentChatId}
        createNewChat={createNewChat}
        deleteChat={deleteChat}
      />
      <ChatBox
        currentChat={currentChat}
        setCurrentChat={updateCurrentChat}
      />
    </div>
  );
}