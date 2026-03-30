export type MessageType = {
  role: "user" | "bot";
  text: string;
  file_url?: string;
  source?: string;
};

export type ChatSession = {
  id: string;
  title: string;
  messages: MessageType[];
};