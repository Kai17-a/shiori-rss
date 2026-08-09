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
      <div class="flex min-h-96 flex-col">
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

        <div class="grid flex-1 place-items-center p-8 text-center">
          <div class="max-w-sm">
            <span class="mx-auto grid size-12 place-items-center rounded-2xl bg-elevated text-muted">
              <UIcon name="i-lucide-message-circle-more" class="size-6" />
            </span>
            <p class="mt-4 font-semibold text-default">Ask about your feed library</p>
            <p class="mt-1 text-sm leading-6 text-muted">
              Article search and AI-generated summaries will be connected in the next step.
            </p>
          </div>
        </div>

        <div class="border-t border-default p-4">
          <UTextarea
            placeholder="Ask a question about saved articles…"
            :rows="2"
            autoresize
            disabled
            class="w-full"
            aria-label="Ask AI message"
          />
        </div>
      </div>
    </template>
  </UModal>
</template>
