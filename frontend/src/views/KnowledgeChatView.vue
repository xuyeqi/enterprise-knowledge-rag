<!--
  知识库问答页。

  页面在当前浏览器会话中保留最近问答，并把最近五轮完整对话传给后端理解追问。
  历史不会写入数据库，刷新页面或点击清空对话后即消失。
-->
<script setup lang="ts">
import { computed, ref } from "vue";

import {
  askKnowledgeBase,
  type ConversationMessage,
  type KnowledgeAnswerResponse,
} from "../api/answer";

const MAX_QUERY_LENGTH = 1000;

const query = ref("");
const isAnswering = ref(false);
const errorMessage = ref("");
const answerResults = ref<KnowledgeAnswerResponse[]>([]);

const canSubmit = computed(() => {
  const normalizedQuery = query.value.trim();
  return (
    normalizedQuery.length > 0 && normalizedQuery.length <= MAX_QUERY_LENGTH
  );
});

/** 把页面中最近五轮完整问答转换为后端约定的交替消息数组。 */
function buildConversationHistory(): ConversationMessage[] {
  return answerResults.value.slice(-5).flatMap(
    (result): ConversationMessage[] => [
      { role: "user", content: result.query },
      { role: "assistant", content: result.answer },
    ],
  );
}

/** 提交清理后的问题，并把本次结果追加到当前页面会话。 */
async function handleAsk(): Promise<void> {
  const normalizedQuery = query.value.trim();

  if (!normalizedQuery) {
    errorMessage.value = "请输入需要查询的问题。";
    return;
  }

  if (normalizedQuery.length > MAX_QUERY_LENGTH) {
    errorMessage.value = `问题不能超过 ${MAX_QUERY_LENGTH} 个字符。`;
    return;
  }

  isAnswering.value = true;
  errorMessage.value = "";

  try {
    const answerResult = await askKnowledgeBase(
      normalizedQuery,
      buildConversationHistory(),
    );
    answerResults.value.push(answerResult);
    query.value = "";
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "知识库问答失败，请稍后重试。";
  } finally {
    isAnswering.value = false;
  }
}

/** 清空当前页面内存中的问答，不发送删除请求，也不修改知识库数据。 */
function clearConversation(): void {
  answerResults.value = [];
  errorMessage.value = "";
  query.value = "";
}

/** 把 0～1 的余弦相似度转换为便于阅读的百分比。 */
function formatSimilarity(similarity: number): string {
  return `${(similarity * 100).toFixed(1)}%`;
}
</script>

<template>
  <section class="chat-page">
    <div class="page-intro">
      <div>
        <p class="section-kicker">KNOWLEDGE ASSISTANT</p>
        <h2>基于企业资料提问</h2>
        <p>系统会先检索相关切片，再由模型根据资料生成带引用的答案。</p>
      </div>
      <span class="phase-number">03</span>
    </div>

    <el-card class="question-card" shadow="never">
      <form class="question-form" @submit.prevent="handleAsk">
        <label for="knowledge-query">你的问题</label>
        <el-input
          id="knowledge-query"
          v-model="query"
          type="textarea"
          :rows="4"
          :maxlength="MAX_QUERY_LENGTH"
          show-word-limit
          resize="vertical"
          placeholder="例如：出差期间产生的打车费如何报销？"
          :disabled="isAnswering"
        />

        <div class="question-form__footer">
          <p
            v-if="errorMessage"
            class="form-message form-message--error"
            role="alert"
          >
            {{ errorMessage }}
          </p>
          <p v-else class="question-hint">
            每次召回最多 1 个切片，并携带最近 5 轮上下文。
          </p>

          <div class="question-actions">
            <el-button
              v-if="answerResults.length > 0"
              native-type="button"
              size="large"
              :disabled="isAnswering"
              @click="clearConversation"
            >
              清空对话
            </el-button>
            <el-button
              native-type="submit"
              type="primary"
              size="large"
              :loading="isAnswering"
              :disabled="!canSubmit"
            >
              {{ isAnswering ? "正在检索并生成答案" : "提交问题" }}
            </el-button>
          </div>
        </div>
      </form>
    </el-card>

    <div v-if="answerResults.length > 0" class="conversation-list">
      <article
        v-for="(answerResult, roundIndex) in answerResults"
        :key="`${roundIndex}-${answerResult.query}`"
        class="answer-layout"
      >
        <el-card class="answer-card" shadow="never">
          <div class="answer-card__header">
            <div>
              <p class="card-label">GROUNDED ANSWER · ROUND {{ roundIndex + 1 }}</p>
              <h3>知识库回答</h3>
            </div>
            <el-tag type="success">{{ answerResult.source_count }} 个来源</el-tag>
          </div>

          <p class="submitted-query">{{ answerResult.query }}</p>
          <div class="answer-content">
            <span class="answer-greeting">您好，</span>{{ answerResult.answer }}
          </div>
        </el-card>

        <section
          class="sources-section"
          :aria-labelledby="`sources-title-${roundIndex}`"
        >
          <div class="sources-heading">
            <div>
              <p class="card-label">EVIDENCE</p>
              <h3 :id="`sources-title-${roundIndex}`">引用来源</h3>
            </div>
            <span>{{ answerResult.source_count }} SOURCES</span>
          </div>

          <el-empty
            v-if="answerResult.sources.length === 0"
            description="本次回答没有可用引用来源"
          />

          <div v-else class="source-list">
            <el-card
              v-for="(source, index) in answerResult.sources"
              :key="source.chunk_id"
              class="source-card"
              shadow="never"
            >
              <div class="source-card__header">
                <strong>[资料{{ index + 1 }}] {{ source.filename }}</strong>
                <span>{{ formatSimilarity(source.similarity) }}</span>
              </div>
              <p class="source-meta">
                切片 #{{ source.chunk_index }}
                <template v-if="source.page_number !== null">
                  · 第 {{ source.page_number }} 页
                </template>
                · 文档 ID：{{ source.document_id }}
              </p>
              <p class="source-content">{{ source.content }}</p>
            </el-card>
          </div>
        </section>
      </article>
    </div>
  </section>
</template>
