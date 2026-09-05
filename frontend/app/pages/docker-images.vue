<template>
  <UDashboardPanel id="docker-images" class="min-w-0">
    <template #header><PageHeaderActions title="Docker images" /></template>
    <template #body>
      <div class="mx-auto w-full min-w-0 max-w-7xl space-y-6 pb-10">
        <UPageCard class="min-w-0 max-w-full" :ui="{ body: 'min-w-0 max-w-full space-y-5' }">
          <div class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Containers</p>
              <h1 class="mt-1 text-2xl font-bold tracking-tight text-highlighted">Docker images</h1>
              <p class="mt-1 text-sm text-muted">Track registry manifest changes for public container images.</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <RefreshButton :loading="refreshing" @click="refreshAll" />
              <UButton label="Add image" icon="i-lucide-plus" @click="openCreate" />
            </div>
          </div>

          <p class="border-b border-default pb-4 text-xs uppercase tracking-[0.08em] text-muted">Total {{ images.total }} images</p>

          <div v-if="images.items.length" class="grid gap-4 lg:grid-cols-2">
            <article v-for="image in images.items" :key="image.id" class="min-w-0 max-w-full space-y-4 rounded-2xl border border-default bg-elevated/30 p-4 sm:p-5">
              <div class="flex min-w-0 items-start justify-between gap-3">
                <div class="min-w-0">
                  <h2 class="max-w-full font-semibold text-highlighted [overflow-wrap:anywhere]">{{ image.display_name }}</h2>
                  <p class="mt-1 text-xs text-muted">Fetched {{ formatDate(image.fetched_at) }}</p>
                </div>
                <div class="flex shrink-0 gap-1">
                  <UButton icon="i-lucide-pencil" aria-label="Edit notification webhooks" color="neutral" variant="ghost" size="sm" @click="openEdit(image)" />
                  <UButton icon="i-lucide-trash-2" aria-label="Delete Docker image" color="error" variant="ghost" size="sm" :loading="deletingId === image.id" loading-icon="i-lucide-loader-circle" @click="askDelete(image)" />
                </div>
              </div>
              <dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
                <dt class="text-muted">Registry</dt><dd class="truncate text-default">{{ image.registry }}</dd>
                <dt class="text-muted">Repository</dt><dd class="text-default [overflow-wrap:anywhere]">{{ image.repository }}</dd>
                <dt class="text-muted">Tag</dt><dd><UBadge color="neutral" variant="soft">{{ image.tag }}</UBadge></dd>
                <dt class="text-muted">Digest</dt><dd class="font-mono text-xs text-default">{{ shortDigest(image.latest_digest) }}</dd>
              </dl>
              <p class="max-w-full text-xs text-muted [overflow-wrap:anywhere]">{{ webhookLabel(image) }}</p>
            </article>
          </div>

          <div v-else class="grid min-h-64 place-items-center rounded-3xl border border-dashed border-default p-8 text-center">
            <div class="max-w-sm space-y-3">
              <UIcon :name="loading ? 'i-lucide-loader-circle' : 'i-lucide-container'" class="mx-auto size-8" :class="{ 'animate-spin': loading }" />
              <p class="font-semibold text-default">{{ loading ? 'Loading images…' : loadError || 'No Docker images registered' }}</p>
              <p v-if="!loading && !loadError" class="text-sm text-muted">Add a public image reference to follow its manifest digest.</p>
            </div>
          </div>
        </UPageCard>

        <UModal v-model:open="modalOpen" :title="form.id ? 'Edit Docker notifications' : 'Add Docker image'" :description="form.id ? 'Choose where image updates are sent.' : 'The current manifest digest is fetched when you save.'">
          <template #body>
            <UForm :state="form" class="space-y-5" @submit="saveImage">
              <UFormField label="Image reference" name="reference" required>
                <UInput v-model="form.reference" placeholder="ghcr.io/owner/name:latest or owner/name" class="w-full" :disabled="Boolean(form.id)" />
              </UFormField>
              <UFormField label="Notification webhooks" description="With none selected, image notifications are disabled.">
                <div v-if="webhooks.length" class="space-y-2">
                  <UCheckbox v-for="webhook in webhooks" :key="webhook.id" :label="webhook.name" :model-value="form.webhook_ids.includes(webhook.id)" @update:model-value="toggleWebhook(webhook.id, $event)" />
                </div>
                <p v-else class="text-sm text-muted">No webhooks are registered. Add one from Preferences.</p>
              </UFormField>
              <div class="flex justify-end gap-2">
                <UButton label="Cancel" color="neutral" variant="ghost" @click="modalOpen = false" />
                <UButton type="submit" :label="form.id ? 'Save notifications' : 'Add image'" :icon="form.id ? 'i-lucide-save' : 'i-lucide-plus'" :loading="saving" loading-icon="i-lucide-loader-circle" />
              </div>
            </UForm>
          </template>
        </UModal>

        <DeleteConfirmModal v-model:open="deleteOpen" title="Delete Docker image" :subject="pendingImage?.display_name" confirm-label="Delete image" :loading="deletingId !== null" @cancel="pendingImage = null" @confirm="confirmDelete" />
      </div>
    </template>
  </UDashboardPanel>
</template>

<script setup lang="ts">
import type { DockerImage, DockerImageListResponse, SettingsWebhookListResponse, SettingsWebhookResponse } from "~/types";

const { request } = useApi();
const toast = useSingleToast();
const images = ref<DockerImageListResponse>({ items: [], total: 0 });
const loading = ref(false);
const refreshing = ref(false);
const saving = ref(false);
const deletingId = ref<number | null>(null);
const loadError = ref("");
const modalOpen = ref(false);
const deleteOpen = ref(false);
const pendingImage = ref<DockerImage | null>(null);
const webhooks = ref<SettingsWebhookResponse[]>([]);
const form = reactive({ id: 0, reference: "", webhook_ids: [] as number[] });

const formatDate = (value: string) => new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
const shortDigest = (digest: string) => digest.startsWith("sha256:") ? `sha256:${digest.slice(7, 19)}` : digest.slice(0, 19);
const errorMessage = (error: unknown, fallback: string) => {
  const detail = (error as { data?: { detail?: string } })?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
};
const webhookLabel = (image: DockerImage) => image.webhook_ids.length
  ? `Notifies ${image.webhook_ids.map((id) => webhooks.value.find((item) => item.id === id)?.name || `Webhook ${id}`).join(", ")}`
  : "Notifications disabled";
const toggleWebhook = (id: number, checked: boolean | string) => {
  const selected = new Set(form.webhook_ids);
  if (checked === true) selected.add(id); else selected.delete(id);
  form.webhook_ids = [...selected];
};
const openCreate = () => { form.id = 0; form.reference = ""; form.webhook_ids = []; modalOpen.value = true; };
const openEdit = (image: DockerImage) => { form.id = image.id; form.reference = image.display_name; form.webhook_ids = [...image.webhook_ids]; modalOpen.value = true; };
const loadImages = async () => {
  loading.value = true; loadError.value = "";
  try { images.value = await request<DockerImageListResponse>("/docker-images"); }
  catch (error) { loadError.value = errorMessage(error, "Could not load Docker images."); }
  finally { loading.value = false; }
};
const refreshAll = async () => {
  refreshing.value = true;
  try {
    images.value = await request<DockerImageListResponse>("/docker-images/refresh", { method: "POST" });
    toast.show({ title: "Image digests updated.", color: "success", icon: "i-lucide-check" });
  } catch (error) { toast.show({ title: errorMessage(error, "Could not update image digests."), color: "error", icon: "i-lucide-circle-alert" }); }
  finally { refreshing.value = false; }
};
const saveImage = async () => {
  if (!form.reference.trim()) return;
  saving.value = true;
  try {
    await request(form.id ? `/docker-images/${form.id}` : "/docker-images", {
      method: form.id ? "PATCH" : "POST",
      body: JSON.stringify(form.id ? { webhook_ids: form.webhook_ids } : { reference: form.reference.trim(), webhook_ids: form.webhook_ids }),
    });
    modalOpen.value = false; await loadImages();
    toast.show({ title: form.id ? "Notification destinations updated." : "Docker image added.", color: "success", icon: "i-lucide-check" });
  } catch (error) { toast.show({ title: errorMessage(error, "Could not add Docker image."), color: "error", icon: "i-lucide-circle-alert" }); }
  finally { saving.value = false; }
};
const askDelete = (image: DockerImage) => { pendingImage.value = image; deleteOpen.value = true; };
const confirmDelete = async () => {
  if (!pendingImage.value) return;
  deletingId.value = pendingImage.value.id;
  try {
    await request(`/docker-images/${pendingImage.value.id}`, { method: "DELETE" });
    deleteOpen.value = false; pendingImage.value = null; await loadImages();
    toast.show({ title: "Docker image deleted.", color: "success", icon: "i-lucide-check" });
  } catch (error) { toast.show({ title: errorMessage(error, "Could not delete Docker image."), color: "error", icon: "i-lucide-circle-alert" }); }
  finally { deletingId.value = null; }
};

onMounted(async () => {
  const [, webhookResponse] = await Promise.all([loadImages(), request<SettingsWebhookListResponse>("/settings/webhooks")]);
  webhooks.value = webhookResponse.items;
});
</script>
