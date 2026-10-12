import { api } from "@/lib/api";
import type { ChatHistoryMessage, ChatResponse, ChatStatus } from "@/lib/types";

/**
 * The assistant is a single non-streaming POST: the backend runs the whole Groq
 * tool-use loop (model asks for a tool, the API executes it against the user's
 * rows, the result goes back to the model) before it answers, so there is
 * nothing to stream until the lookups are done.
 */
export async function sendChatMessage(
  message: string,
  history: ChatHistoryMessage[],
): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/chat", { message, history });
  return data;
}

/** Whether a Groq key is configured, so the UI can explain itself instead of failing. */
export async function fetchChatStatus(): Promise<ChatStatus> {
  const { data } = await api.get<ChatStatus>("/chat/status");
  return data;
}
