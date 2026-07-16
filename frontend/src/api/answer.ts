/**
 * 知识库问答接口。
 *
 * 普通接口保留一次性 JSON 响应；聊天页面使用 `POST /answer/stream`，通过 SSE
 * 逐块接收模型答案，并在生成结束时接收真正交给模型的引用切片。
 */
import { request, requestResponse } from "./http";

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

/** 浏览器从 SSE 文本中解析出的一条完整事件。 */
interface ServerSentEvent {
  event: string;
  data: unknown;
}

/** 把一段以空行结尾的 SSE 文本解析为事件名和 JSON 数据。 */
function parseServerSentEvent(block: string): ServerSentEvent | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    event,
    data: JSON.parse(dataLines.join("\n")) as unknown,
  };
}

/** 确认 JSON 数据是普通对象，避免直接读取 unknown 类型的属性。 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
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

/**
 * 提交流式知识库问答，并在每次收到答案增量时通知页面更新。
 *
 * 网络分块不等于 SSE 事件边界，因此函数会把未完成文本保留在 buffer 中，只有
 * 遇到空行时才解析完整事件。返回值与普通接口保持一致，方便页面保存对话历史。
 */
export async function askKnowledgeBaseStream(
  query: string,
  history: ConversationMessage[],
  onDelta: (content: string) => void,
  limit = 1,
): Promise<KnowledgeAnswerResponse> {
  const response = await requestResponse("/answer/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ query, history, limit }),
  });
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("浏览器没有返回可读取的回答数据流。");
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let answer = "";
  let sources: AnswerSource[] = [];
  let isDone = false;

  const handleEvent = (block: string): void => {
    const message = parseServerSentEvent(block);
    if (!message) {
      return;
    }

    if (message.event === "delta") {
      if (!isRecord(message.data) || typeof message.data.content !== "string") {
        throw new Error("流式回答返回了无效的文本事件。");
      }
      answer += message.data.content;
      onDelta(message.data.content);
      return;
    }

    if (message.event === "sources") {
      if (!isRecord(message.data) || !Array.isArray(message.data.sources)) {
        throw new Error("流式回答返回了无效的引用来源。");
      }
      sources = message.data.sources as AnswerSource[];
      return;
    }

    if (message.event === "done") {
      isDone = true;
      return;
    }

    if (message.event === "error") {
      const errorMessage =
        isRecord(message.data) && typeof message.data.message === "string"
          ? message.data.message
          : "回答生成中断，请稍后重试。";
      throw new Error(errorMessage);
    }
  };

  const consumeCompleteEvents = (): void => {
    buffer = buffer.replace(/\r\n/g, "\n");
    let boundaryIndex = buffer.indexOf("\n\n");

    while (boundaryIndex !== -1) {
      const block = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);
      if (block.trim()) {
        handleEvent(block);
      }
      boundaryIndex = buffer.indexOf("\n\n");
    }
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      consumeCompleteEvents();
    }

    buffer += decoder.decode();
    consumeCompleteEvents();
    if (buffer.trim()) {
      handleEvent(buffer);
    }
  } catch (error) {
    // 解析到服务端 error 事件或无效数据后主动取消读取，避免留下无人消费的响应流。
    await reader.cancel().catch(() => undefined);
    throw error;
  } finally {
    reader.releaseLock();
  }

  if (!isDone) {
    throw new Error("流式回答意外中断，请稍后重试。");
  }

  return {
    query,
    answer,
    source_count: sources.length,
    sources,
  };
}
