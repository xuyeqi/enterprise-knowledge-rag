/**
 * 知识库问答接口。
 *
 * 页面把用户问题提交给后端 `POST /answer`。后端完成 embedding 检索、LangChain
 * 上下文组装和模型生成后，返回自然语言答案及真正交给模型的引用切片。
 */
import { request } from "./http";

/** 一条引用来源，对应 PostgreSQL 中的一个文档切片。 */
export interface AnswerSource {
  chunk_id: string;
  document_id: string;
  filename: string;
  chunk_index: number;
  page_number: number | null;
  content: string;
  similarity: number;
}

/** 后端一次完整知识库问答的响应。 */
export interface KnowledgeAnswerResponse {
  query: string;
  answer: string;
  source_count: number;
  sources: AnswerSource[];
}

/** 一条已经完成的对话消息，用于帮助后端理解指代和追问。 */
export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

/**
 * 提交问题并返回答案与引用来源。
 *
 * @param query 用户输入的问题，页面会先去除首尾空白。
 * @param history 最近五轮已经完成的对话，默认没有历史消息。
 * @param limit 最多召回并交给模型的切片数量，当前页面默认使用 1。
 */
export function askKnowledgeBase(
  query: string,
  history: ConversationMessage[] = [],
  limit = 1,
): Promise<KnowledgeAnswerResponse> {
  return request<KnowledgeAnswerResponse>("/answer", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query, history, limit }),
  });
}
