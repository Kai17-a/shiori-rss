<template>
  <UModal
    title="Ask AI"
    description="Search and summarize articles saved in Shiori Feed."
    :ui="{ content: 'sm:max-w-xl' }"
  >
    <div class="fixed bottom-4 right-4 z-40 sm:bottom-6 sm:right-6">
      <UButton
        label="Ask AI"
        icon="i-lucide-sparkles"
        size="lg"
        class="rounded-full px-5 shadow-lg shadow-primary/20"
        aria-label="Open Ask AI chat"
      />
    </div>

    <template #content="{ close }">
      <div class="flex max-h-[min(42rem,calc(100dvh-2rem))] min-h-96 flex-col">
        <header class="flex items-start justify-between gap-4 border-b border-default p-5">
          <div class="flex items-center gap-3">
            <span class="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
              <UIcon name="i-lucide-sparkles" class="size-5" />
            </span>
            <div>
              <h2 class="font-semibold text-highlighted">Ask AI</h2>
              <p class="text-sm text-muted">Search and summarize your saved articles.</p>
            </div>
          </div>
          <IconButton
            label="Close Ask AI"
            icon="i-lucide-x"
            color="neutral"
            variant="ghost"
            @click="close"
          />
        </header>

        <div v-if="messages.length === 0" class="grid flex-1 place-items-center p-8 text-center">
          <div class="max-w-sm">
            <span class="mx-auto grid size-12 place-items-center rounded-2xl bg-elevated text-muted">
              <UIcon name="i-lucide-message-circle-more" class="size-6" />
            </span>
            <p class="mt-4 font-semibold text-default">Ask about your feed library</p>
            <p class="mt-1 text-sm leading-6 text-muted">
              Ask a question to search and summarize articles saved in Shiori Feed.
            </p>
          </div>
        </div>

        <div v-else class="flex-1 space-y-5 overflow-y-auto p-5" aria-live="polite">
          <div v-for="(message, index) in messages" :key="index" class="space-y-3">
            <div class="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-sm text-inverted">
              {{ message.question }}
            </div>
            <div class="max-w-[92%] rounded-2xl rounded-bl-md bg-elevated px-4 py-3">
              <LazyUEditor
                :model-value="message.answer"
                content-type="markdown"
                :editable="false"
                :image="false"
                :mention="false"
                :starter-kit="readOnlyEditorOptions"
                aria-label="Ask AI answer"
                :ui="{
                  base: 'sm:px-0 text-sm [&_h1]:text-xl [&_h2]:text-lg [&_h3]:text-base',
                }"
              />
              <div v-if="message.sources.length" class="mt-4 space-y-2 border-t border-default pt-3">
                <p class="text-xs font-semibold uppercase tracking-wide text-muted">Sources</p>
                <a
                  v-for="(source, sourceIndex) in message.sources"
                  :key="`${source.source_type}-${source.article_id}`"
                  :href="source.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-start gap-2 rounded-lg p-2 text-sm hover:bg-accented"
                >
                  <span class="font-mono text-xs text-muted">S{{ sourceIndex + 1 }}</span>
                  <span class="min-w-0">
                    <span class="block truncate font-medium text-highlighted">
                      {{ source.title || source.url }}
                    </span>
                    <span class="block truncate text-xs text-muted">{{ source.source_title }}</span>
                  </span>
                </a>
              </div>
            </div>
          </div>
          <div v-if="loading" class="flex items-center gap-2 text-sm text-muted" role="status">
            <UIcon name="i-lucide-loader-circle" class="size-4 animate-spin" />
            Searching saved articles…
          </div>
        </div>

        <div v-if="errorMessage" class="px-4 pt-4">
          <UAlert
            color="error"
            variant="subtle"
            icon="i-lucide-circle-alert"
            :description="errorMessage"
          />
        </div>

        <form class="flex items-end gap-2 border-t border-default p-4" @submit.prevent="submitQuestion">
          <UTextarea
            v-model="question"
            placeholder="Ask a question about saved articles…"
            :rows="2"
            autoresize
            class="w-full"
            aria-label="Ask AI message"
            :disabled="loading"
            @keydown.enter.exact.prevent="submitQuestion"
          />
          <UButton
            type="submit"
            icon="i-lucide-send"
            label="Send"
            :loading="loading"
            :disabled="!question.trim() || loading"
          />
        </form>
      </div>
    </template>
  </UModal>
</template>

<script setup lang="ts">
import type { AskAIResponse, AskAISource } from "~/types";

interface ChatExchange {
  question: string;
  answer: string;
  sources: AskAISource[];
}

const { request } = useApi();
const question = ref("");
const loading = ref(false);
const errorMessage = ref("");
const messages = ref<ChatExchange[]>([]);
const readOnlyEditorOptions = {
  link: {
    openOnClick: true,
    HTMLAttributes: {
      target: "_blank",
      rel: "noopener noreferrer",
    },
  },
};

const submitQuestion = async () => {
  const message = question.value.trim();
  if (!message || loading.value) return;

  loading.value = true;
  errorMessage.value = "";
  question.value = "";
  try {
    const response = await request<AskAIResponse>("/ai/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    messages.value.push({ question: message, ...response });
  } catch (error) {
    question.value = message;
    errorMessage.value = error instanceof Error ? error.message : "Ask AI request failed.";
  } finally {
    loading.value = false;
  }
};
</script>
