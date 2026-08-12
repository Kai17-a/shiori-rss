<template>
  <UDashboardPanel id="github-releases">
    <template #header><PageHeaderActions title="GitHub" /></template>
    <template #body>
      <div class="mx-auto w-full max-w-7xl space-y-6 pb-10">
        <UPageCard :ui="{ body: 'space-y-5' }">
          <div class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Releases</p>
              <h1 class="mt-1 text-2xl font-bold tracking-tight text-highlighted">GitHub repositories</h1>
              <p class="mt-1 text-sm text-muted">Track the latest published release for each registered tool.</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <RefreshButton :loading="refreshing" @click="refreshAll" />
              <UButton label="Add repository" icon="i-lucide-plus" @click="openCreate" />
            </div>
          </div>

          <p class="border-b border-default pb-4 text-xs uppercase tracking-[0.08em] text-muted">
            Total {{ repositories.total }} repositories
          </p>

          <div v-if="repositories.items.length" class="grid gap-4 lg:grid-cols-2">
            <article v-for="repository in repositories.items" :key="repository.id" class="space-y-4 rounded-2xl border border-default bg-elevated/30 p-5">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <a :href="repository.repository_url" target="_blank" rel="noreferrer" class="font-semibold text-highlighted hover:text-primary hover:underline">
                    {{ repository.owner }}/{{ repository.repository }}
                  </a>
                  <p class="mt-1 text-xs text-muted">Updated {{ formatDate(repository.fetched_at) }}</p>
                </div>
                <div class="flex gap-1">
                  <UButton icon="i-lucide-pencil" aria-label="Edit notification webhooks" color="neutral" variant="ghost" size="sm" @click="openEdit(repository)" />
                  <UButton icon="i-lucide-trash-2" aria-label="Delete repository" color="error" variant="ghost" size="sm" :loading="deletingId === repository.id" loading-icon="i-lucide-loader-circle" @click="askDelete(repository)" />
                </div>
              </div>
              <div>
                <div class="flex flex-wrap items-center gap-2">
                  <h2 class="font-semibold text-default">{{ repository.latest_release_name }}</h2>
                  <UBadge color="neutral" variant="soft">{{ repository.latest_release_tag }}</UBadge>
                </div>
                <p class="mt-1 text-xs text-muted">Published {{ formatDate(repository.latest_release_published_at) }}</p>
                <p class="mt-2 text-xs text-muted">{{ webhookLabel(repository) }}</p>
                <p v-if="repository.latest_release_body" class="mt-3 line-clamp-3 whitespace-pre-line text-sm text-muted">{{ repository.latest_release_body }}</p>
              </div>
              <UButton :to="repository.latest_release_url" target="_blank" label="View release" trailing-icon="i-lucide-external-link" color="neutral" variant="soft" />
            </article>
          </div>

          <div v-else class="grid min-h-64 place-items-center rounded-3xl border border-dashed border-default p-8 text-center">
            <div class="max-w-sm space-y-3">
              <UIcon :name="loading ? 'i-lucide-loader-circle' : 'i-lucide-github'" class="mx-auto size-8" :class="{ 'animate-spin': loading }" />
              <p class="font-semibold text-default">{{ loading ? 'Loading repositories…' : loadError || 'No repositories registered' }}</p>
              <p v-if="!loading && !loadError" class="text-sm text-muted">Add a public GitHub repository URL to follow its latest release.</p>
            </div>
          </div>
        </UPageCard>

        <UModal v-model:open="modalOpen" :title="form.id ? 'Edit GitHub notifications' : 'Add GitHub repository'" :description="form.id ? 'Choose where new releases are sent.' : 'The latest published release is fetched when you save.'">
          <template #body>
            <UForm :state="form" class="space-y-5" @submit="saveRepository">
              <UFormField label="Repository URL" name="repository_url" required>
                <UInput v-model="form.repository_url" placeholder="https://github.com/owner/repository" class="w-full" :disabled="Boolean(form.id)" />
              </UFormField>
              <UFormField label="Notification webhooks" description="With none selected, release notifications are disabled.">
                <div v-if="webhooks.length" class="space-y-2">
                  <UCheckbox v-for="webhook in webhooks" :key="webhook.id" :label="webhook.name" :model-value="form.webhook_ids.includes(webhook.id)" @update:model-value="toggleWebhook(webhook.id, $event)" />
                </div>
                <p v-else class="text-sm text-muted">No webhooks are registered. Add one from Preferences.</p>
              </UFormField>
              <div class="flex justify-end gap-2">
                <UButton label="Cancel" color="neutral" variant="ghost" @click="modalOpen = false" />
                <UButton type="submit" :label="form.id ? 'Save notifications' : 'Add repository'" :icon="form.id ? 'i-lucide-save' : 'i-lucide-plus'" :loading="saving" loading-icon="i-lucide-loader-circle" />
              </div>
            </UForm>
          </template>
        </UModal>

        <DeleteConfirmModal v-model:open="deleteOpen" title="Delete GitHub repository" :subject="pendingRepository ? `${pendingRepository.owner}/${pendingRepository.repository}` : undefined" confirm-label="Delete repository" :loading="deletingId !== null" @cancel="pendingRepository = null" @confirm="confirmDelete" />
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { GitHubRepository, GitHubRepositoryListResponse, SettingsWebhookListResponse, SettingsWebhookResponse } from "~/types";

const { request } = useApi();
const toast = useSingleToast();
const repositories = ref<GitHubRepositoryListResponse>({ items: [], total: 0 });
const loading = ref(false);
const refreshing = ref(false);
const saving = ref(false);
const deletingId = ref<number | null>(null);
const loadError = ref("");
const modalOpen = ref(false);
const deleteOpen = ref(false);
const pendingRepository = ref<GitHubRepository | null>(null);
const webhooks = ref<SettingsWebhookResponse[]>([]);
const form = reactive({ id: 0, repository_url: "", webhook_ids: [] as number[] });

const formatDate = (value: string) => new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
const errorMessage = (error: unknown, fallback: string) => {
  const detail = (error as { data?: { detail?: string } })?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
};
const webhookLabel = (repository: GitHubRepository) => repository.webhook_ids.length
  ? `Notifies ${repository.webhook_ids.map((id) => webhooks.value.find((item) => item.id === id)?.name || `Webhook ${id}`).join(", ")}`
  : "Notifications disabled";
const toggleWebhook = (id: number, checked: boolean | string) => {
  const selected = new Set(form.webhook_ids);
  if (checked === true) selected.add(id); else selected.delete(id);
  form.webhook_ids = [...selected];
};
const openCreate = () => { form.id = 0; form.repository_url = ""; form.webhook_ids = []; modalOpen.value = true; };
const openEdit = (repository: GitHubRepository) => { form.id = repository.id; form.repository_url = repository.repository_url; form.webhook_ids = [...repository.webhook_ids]; modalOpen.value = true; };
const loadRepositories = async () => {
  loading.value = true; loadError.value = "";
  try { repositories.value = await request<GitHubRepositoryListResponse>("/github-repositories"); }
  catch (error) { loadError.value = errorMessage(error, "Could not load GitHub repositories."); }
  finally { loading.value = false; }
};
const refreshAll = async () => {
  refreshing.value = true;
  try {
    repositories.value = await request<GitHubRepositoryListResponse>("/github-repositories/refresh", { method: "POST" });
    toast.show({ title: "Latest releases updated.", color: "success", icon: "i-lucide-check" });
  } catch (error) { toast.show({ title: errorMessage(error, "Could not update releases."), color: "error", icon: "i-lucide-circle-alert" }); }
  finally { refreshing.value = false; }
};
const saveRepository = async () => {
  if (!form.repository_url.trim()) return;
  saving.value = true;
  try {
    await request(form.id ? `/github-repositories/${form.id}` : "/github-repositories", {
      method: form.id ? "PATCH" : "POST",
      body: JSON.stringify(form.id ? { webhook_ids: form.webhook_ids } : { repository_url: form.repository_url.trim(), webhook_ids: form.webhook_ids }),
    });
    modalOpen.value = false; await loadRepositories();
    toast.show({ title: form.id ? "Notification destinations updated." : "GitHub repository added.", color: "success", icon: "i-lucide-check" });
  } catch (error) { toast.show({ title: errorMessage(error, "Could not add repository."), color: "error", icon: "i-lucide-circle-alert" }); }
  finally { saving.value = false; }
};
const askDelete = (repository: GitHubRepository) => { pendingRepository.value = repository; deleteOpen.value = true; };
const confirmDelete = async () => {
  if (!pendingRepository.value) return;
  deletingId.value = pendingRepository.value.id;
  try {
    await request(`/github-repositories/${pendingRepository.value.id}`, { method: "DELETE" });
    deleteOpen.value = false; pendingRepository.value = null; await loadRepositories();
    toast.show({ title: "GitHub repository deleted.", color: "success", icon: "i-lucide-check" });
  } catch (error) { toast.show({ title: errorMessage(error, "Could not delete repository."), color: "error", icon: "i-lucide-circle-alert" }); }
  finally { deletingId.value = null; }
};

onMounted(async () => {
  const [, webhookResponse] = await Promise.all([
    loadRepositories(),
    request<SettingsWebhookListResponse>("/settings/webhooks"),
  ]);
  webhooks.value = webhookResponse.items;
});
</script>
