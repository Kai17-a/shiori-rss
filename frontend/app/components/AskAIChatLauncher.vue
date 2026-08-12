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

        <UChatMessages
          v-else
          :messages="uiMessages"
          :status="chatStatus"
          should-auto-scroll
          :auto-scroll="false"
          class="flex-1 space-y-5 overflow-y-auto p-5"
          aria-live="polite"
        >
          <div v-for="message in messages" :key="message.id" class="space-y-3">
            <div class="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-sm text-inverted">
              {{ message.question }}
            </div>
            <div
              v-if="message.answer || message.sources.length || !isActiveExchange(message)"
              class="max-w-[92%] rounded-2xl rounded-bl-md bg-elevated px-4 py-3"
            >
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
                  v-for="source in message.sources"
                  :key="`${source.source_type}-${source.article_id}`"
                  :href="source.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-start gap-2 rounded-lg p-2 text-sm hover:bg-accented"
                >
                  <span class="font-mono text-xs text-muted">{{ source.reference }}</span>
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
        </UChatMessages>

        <div v-if="errorMessage" class="px-4 pt-4">
          <UAlert
            color="error"
            variant="subtle"
            icon="i-lucide-circle-alert"
            :description="errorMessage"
          />
        </div>

        <div class="border-t border-default p-4">
          <UChatPrompt
            v-model="question"
            placeholder="Ask a question about saved articles…"
            :rows="2"
            :disabled="loading"
            aria-label="Ask AI message"
            @submit="submitQuestion"
          >
            <template #footer>
              <div class="flex justify-end">
                <UChatPromptSubmit
                  label="Send"
                  aria-label="Send"
                  icon="i-lucide-send"
                  :status="chatStatus"
                  :disabled="!question.trim() && !loading"
                  @stop="stopStreaming"
                  @reload="submitQuestion"
                />
              </div>
            </template>
          </UChatPrompt>
        </div>
      </div>
    </template>
  </UModal>
</template>

<script setup lang="ts">
import type { AskAISource } from "~/types";

type ChatStatus = "ready" | "submitted" | "streaming" | "error";

type StreamEvent =
  | { type: "sources"; sources: AskAISource[] }
  | { type: "delta"; delta: string }
  | { type: "done" }
  | { type: "error"; detail: string };

interface ChatExchange {
  id: string;
  question: string;
  answer: string;
  sources: AskAISource[];
}

const { defaultApiBase } = useApi();
const question = ref("");
const chatStatus = ref<ChatStatus>("ready");
const errorMessage = ref("");
const messages = ref<ChatExchange[]>([]);
const activeController = shallowRef<AbortController | null>(null);
const loading = computed(() => ["submitted", "streaming"].includes(chatStatus.value));
const uiMessages = computed(() => messages.value.flatMap((message) => [
  {
    id: `user-${message.id}`,
    role: "user" as const,
    parts: [{ type: "text" as const, text: message.question }],
  },
  {
    id: `assistant-${message.id}`,
    role: "assistant" as const,
    parts: message.answer ? [{ type: "text" as const, text: message.answer }] : [],
  },
]));
const readOnlyEditorOptions = {
  link: {
    openOnClick: true,
    HTMLAttributes: {
      target: "_blank",
      rel: "noopener noreferrer",
    },
  },
};

const isActiveExchange = (message: ChatExchange) =>
  loading.value && messages.value.at(-1)?.id === message.id;

const errorFromResponse = async (response: Response) => {
  const body = await response.json().catch(() => null) as { detail?: string } | null;
  return body?.detail || `HTTP ${response.status}`;
};

const applyStreamEvent = (exchange: ChatExchange, event: StreamEvent) => {
  if (event.type === "sources") {
    exchange.sources = event.sources;
    chatStatus.value = "streaming";
  } else if (event.type === "delta") {
    exchange.answer += event.delta;
    chatStatus.value = "streaming";
  } else if (event.type === "error") {
    throw new Error(event.detail);
  }
};

const readStream = async (response: Response, exchange: ChatExchange) => {
  if (!response.body) throw new Error("Ask AI returned an empty stream.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const lines = buffer.split("\n");
    buffer = done ? "" : lines.pop() || "";
    for (const line of lines) {
      if (line.trim()) applyStreamEvent(exchange, JSON.parse(line) as StreamEvent);
    }
    if (done) break;
  }
  if (buffer.trim()) applyStreamEvent(exchange, JSON.parse(buffer) as StreamEvent);
};

const stopStreaming = () => {
  activeController.value?.abort();
};

const submitQuestion = async () => {
  const message = question.value.trim();
  if (!message || loading.value) return;

  chatStatus.value = "submitted";
  errorMessage.value = "";
  question.value = "";
  const exchange: ChatExchange = {
    id: crypto.randomUUID(),
    question: message,
    answer: "",
    sources: [],
  };
  messages.value.push(exchange);
  const previousMessages = messages.value.slice(0, -1).slice(-4);
  const history = previousMessages.flatMap((item) => [
    { role: "user", content: item.question },
    ...(item.answer ? [{ role: "assistant", content: item.answer }] : []),
  ]);
  const contextSources = previousMessages.at(-1)?.sources.slice(0, 10) || [];
  const controller = new AbortController();
  activeController.value = controller;
  try {
    const response = await fetch(`${defaultApiBase}/ai/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history, context_sources: contextSources }),
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(await errorFromResponse(response));
    await readStream(response, exchange);
    chatStatus.value = "ready";
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      chatStatus.value = "ready";
    } else {
      question.value = message;
      chatStatus.value = "error";
      errorMessage.value = error instanceof Error ? error.message : "Ask AI request failed.";
    }
  } finally {
    activeController.value = null;
  }
};
</script>
