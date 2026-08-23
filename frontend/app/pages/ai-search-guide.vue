<template>
  <UDashboardPanel id="ai-search-guide" class="min-w-0">
    <template #header>
      <PageHeaderActions title="About AI search">
        <UButton
          to="/settings?tab=llm"
          label="LLM settings"
          icon="i-lucide-settings"
          color="neutral"
          variant="ghost"
        />
      </PageHeaderActions>
    </template>

    <template #body>
      <div class="mx-auto w-full min-w-0 max-w-3xl space-y-6 pb-10">
        <UPageCard :ui="{ body: 'space-y-6' }">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Ask AI</p>
            <h1 class="mt-1 text-2xl font-bold tracking-tight text-highlighted">
              How article search works
            </h1>
          </div>

          <section class="space-y-2">
            <h2 class="text-base font-semibold text-highlighted">Keyword search (always on)</h2>
            <p class="text-sm leading-6 text-muted">
              When you ask a question, an LLM reads it and extracts search keywords, then looks
              for saved articles whose title, summary, or AI-generated metadata match those
              keywords. The best matches are handed back to the LLM, which answers your question
              and cites the articles it used. This works out of the box and needs no extra setup.
            </p>
          </section>

          <section class="space-y-2">
            <h2 class="text-base font-semibold text-highlighted">
              Semantic search (optional)
            </h2>
            <p class="text-sm leading-6 text-muted">
              Keyword search can miss articles that discuss the same thing in different words. If
              you configure an embedding model, your question is also compared directly against a
              numeric representation of each saved article's meaning, so paraphrases and related
              concepts are found even without shared keywords — for example, asking about
              "layoffs" can surface an article about a "workforce reduction."
            </p>
          </section>

          <section class="space-y-2">
            <h2 class="text-base font-semibold text-highlighted">Enabling it</h2>
            <p class="text-sm leading-6 text-muted">
              Set an
              <span class="font-medium text-default">Embedding model</span>
              in
              <NuxtLink to="/settings?tab=llm" class="text-primary hover:underline">
                Preferences &rarr; LLM connection
              </NuxtLink>. It must be an embedding-capable model, not a chat model — for example
              <code class="rounded bg-elevated px-1 py-0.5 text-xs">nomic-embed-text</code>
              for Ollama, or
              <code class="rounded bg-elevated px-1 py-0.5 text-xs">text-embedding-3-small</code>
              for an OpenAI-compatible provider. It reuses the same provider, base URL, and API
              key as your chat connection.
            </p>
          </section>

          <section class="space-y-2">
            <h2 class="text-base font-semibold text-highlighted">What happens next</h2>
            <p class="text-sm leading-6 text-muted">
              There is no separate button to press. Saved articles are embedded automatically the
              next time the
              <NuxtLink to="/ai-data" class="text-primary hover:underline">
                article analysis batch
              </NuxtLink>
              runs, alongside the existing AI summary step. Changing the embedding model later
              re-embeds articles automatically on the next run. Turning it off does not delete
              anything already embedded — search just goes back to keywords only.
            </p>
          </section>

          <UAlert
            title="Fully optional"
            description="Ask AI works completely without an embedding model configured. This only adds a second way to find relevant articles."
            color="neutral"
            variant="soft"
            icon="i-lucide-info"
          />
        </UPageCard>
      </div>
    </template>
  </UDashboardPanel>
</template>
