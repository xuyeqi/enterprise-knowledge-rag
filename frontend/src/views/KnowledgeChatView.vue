<!--
  知识库问答页。

  当前阶段只展示最近一次问题、答案和引用来源。对话历史与流式输出属于阶段 4，
  这里不提前引入额外状态结构或流式协议。
-->
<script setup lang="ts">
import { computed, ref } from "vue";

import { askKnowledgeBase, type KnowledgeAnswerResponse } from "../api/answer";

const MAX_QUERY_LENGTH = 1000;

const query = ref("");
const isAnswering = ref(false);
const errorMessage = ref("");
const answerResult = ref<KnowledgeAnswerResponse | null>(null);

const canSubmit = computed(() => {
  const normalizedQuery = query.value.trim();
  return (
    normalizedQuery.length > 0 && normalizedQuery.length <= MAX_QUERY_LENGTH
  );
});

/** 提交清理后的问题，并用本次响应替换上一次问答结果。 */
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
  answerResult.value = null;

  try {
    answerResult.value = await askKnowledgeBase(normalizedQuery);
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "知识库问答失败，请稍后重试。";
  } finally {
    isAnswering.value = false;
  }
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
            每次问答默认召回最多 3 个知识库切片。
          </p>

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
      </form>
    </el-card>

    <div v-if="answerResult" class="answer-layout">
      <el-card class="answer-card" shadow="never">
        <div class="answer-card__header">
          <div>
            <p class="card-label">GROUNDED ANSWER</p>
            <h3>知识库回答</h3>
          </div>
          <el-tag type="success">{{ answerResult.source_count }} 个来源</el-tag>
        </div>

        <p class="submitted-query">{{ answerResult.query }}</p>
        <div class="answer-content">
          <span class="answer-greeting">您好，</span>{{ answerResult.answer }}
        </div>
      </el-card>

      <section class="sources-section" aria-labelledby="sources-title">
        <div class="sources-heading">
          <div>
            <p class="card-label">EVIDENCE</p>
            <h3 id="sources-title">引用来源</h3>
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
              切片 #{{ source.chunk_index }} · 文档 ID：{{ source.document_id }}
            </p>
            <p class="source-content">{{ source.content }}</p>
          </el-card>
        </div>
      </section>
    </div>
  </section>
</template>
