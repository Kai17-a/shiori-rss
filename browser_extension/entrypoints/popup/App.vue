<template>
  <div class="min-h-screen px-2 py-3">
    <div class="mx-auto w-full flex-col max-w-85 min-w-85 gap-2">
      <div class="flex items-center justify-between px-1">
        <h1 class="text-xl font-bold mb-2">Shiori Keeper</h1>
        <Button
          icon="pi pi-times"
          severity="contrast"
          variant="text"
          raised
          rounded
          aria-label="Cancel"
          @click="closePopup"
        />
      </div>

      <Card>
        <template #content>
          <div class="flex flex-col gap-2">
            <label for="api-server-url">API Server URL</label>
            <div class="flex items-center gap-2">
              <InputText
                id="api-server-url"
                v-model="apiUrl"
                type="text"
                size="small"
                class="w-full"
              />
              <Button
                icon="pi pi-refresh"
                severity="success"
                aria-label="Reload"
                size="small"
                :loading="isHealthChecking"
                @click="connectApiServer"
              />
            </div>
            <Message size="small" :severity="apiStatusMessageColor" variant="simple">
              {{ apiStatusMessage }}
            </Message>
          </div>
        </template>
      </Card>

      <Card class="mt-2">
        <template #content>
          <div class="flex flex-col gap-2">
            <label for="title">Title</label>
            <InputText id="title" v-model="state.title" type="text" size="small" />
          </div>

          <div class="flex flex-col gap-2 mt-2">
            <label for="url">URL</label>
            <InputText id="url" v-model="state.url" type="text" size="small" />
          </div>

          <div class="flex flex-col gap-2 mt-2">
            <label for="description">Description</label>
            <Textarea
              id="description"
              v-model="state.description"
              rows="2"
              cols="30"
              size="small"
            />
          </div>

          <div class="mt-2">
            <div class="flex items-center justify gap-2">
              <div class="flex flex-col gap-2 w-full">
                <label for="folder">Folder</label>
                <Select
                  id="folder"
                  v-model="state.folder"
                  :options="folderItems"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Select a Folder"
                  size="small"
                  class="md:w-56"
                />
              </div>
              <div class="flex flex-col gap-2 w-full">
                <label for="tag">Tag</label>
                <MultiSelect
                  id="tag"
                  v-model="state.tag"
                  :options="tagItems"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Select Tags"
                  :maxSelectedLabels="2"
                  size="small"
                  class="md:w-80"
                />
              </div>
            </div>
          </div>
        </template>
      </Card>

      <div class="flex items-center justify-between gap-3 px-1 pt-1 mt-2">
        <Message
          size="small"
          :severity="responseMessageColor"
          variant="simple"
          class="text-xs font-medium"
        >
          {{ responseMessage }}
        </Message>
        <div class="ml-auto flex items-center gap-3">
          <Button label="Remove" severity="danger" size="small" @click="remove" />
          <Button label="Save" size="small" @click="save" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import {
  createConnectedPopupInitializer,
  createBookmark,
  upsertBookmark,
} from "../../utils/popupBookmark";

// health check
const isHealthChecking = ref(false);
const isApiServerConnect = ref(false);
const apiStatusMessageColor = ref("warn");
const apiStatusMessage = ref("Connecting to API...");
const apiUrl = ref("http://localhost:8000");

// api
const pending = ref(false);
const responseMessage = ref("");
const responseMessageColor = ref("warn");

// form value
const state = reactive({
  title: "",
  url: "",
  description: "",
  folder: null as number | null,
  tag: [] as number[],
});

// select
const folderItems = ref<{ label: string; value: number }[]>([]);
const tagItems = ref<{ label: string; value: number }[]>([]);

const getActiveTab = async () => {
  const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
  return tab;
};

const API_URL_STORAGE_KEY = "popup_api_url";

const loadApiUrl = async () => {
  const result = await browser.storage.local.get(API_URL_STORAGE_KEY);
  const storedApiUrl = result[API_URL_STORAGE_KEY];
  if (typeof storedApiUrl === "string" && storedApiUrl.trim()) {
    apiUrl.value = storedApiUrl;
  }
};

const saveApiUrl = async (value: string) => {
  await browser.storage.local.set({ [API_URL_STORAGE_KEY]: value });
};

const initializeConnectedApi = createConnectedPopupInitializer();

const closePopup = () => {
  window.close();
};

const formatApiError = (body: unknown, status: number) => {
  if (typeof body === "string") return body;
  if (body && typeof body === "object") {
    const detail = (body as { detail?: unknown }).detail;
    if (
      Array.isArray(detail) &&
      detail.every((item) => item && typeof item === "object" && "msg" in item)
    ) {
      return detail
        .map((item) => String((item as { msg?: unknown }).msg ?? ""))
        .filter(Boolean)
        .join("\n");
    }
    if (detail != null) return JSON.stringify(detail);
    return JSON.stringify(body);
  }
  return `HTTP ${status}`;
};

const connectApiServer = async () => {
  if (isHealthChecking.value) return;

  isHealthChecking.value = true;

  try {
    const response = await fetch(new URL("/health", apiUrl.value));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    } else {
      apiStatusMessage.value = "Connected to API";
      apiStatusMessageColor.value = "success";
    }
    isApiServerConnect.value = true;
    await initializeConnectedApi(apiUrl.value, { register, getFolders, getTags });
  } catch (error) {
    apiStatusMessage.value = "Failed to Connect to API";
    apiStatusMessageColor.value = "error";
  } finally {
    isHealthChecking.value = false;
  }
};

const loadExistingBookmark = async () => {
  const url = new URL("/bookmarks/by-url", apiUrl.value);
  url.searchParams.set("url", state.url);

  const response = await fetch(url);
  if (response.status === 404) {
    return false;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(formatApiError(body, response.status));
  }

  const bookmark = await response.json();
  state.title = bookmark.title ?? state.title;
  state.description = bookmark.description ?? "";
  state.folder = bookmark.folder_id ?? null;
  state.tag = Array.isArray(bookmark.tags)
    ? bookmark.tags.map((tag: { id: number }) => tag.id)
    : [];
  return true;
};

const register = async () => {
  if (pending.value) {
    return;
  }

  pending.value = true;

  try {
    const response = await createBookmark(apiUrl.value, state);

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(formatApiError(body, response.status));
    }

    responseMessageColor.value = "success";
    responseMessage.value = "Registered";
  } catch (error) {
    responseMessageColor.value = "error";
    responseMessage.value = error instanceof Error ? error.message : String(error);
  } finally {
    pending.value = false;
  }
};

const save = async () => {
  if (pending.value) {
    return;
  }

  pending.value = true;
  responseMessageColor.value = "warn";
  responseMessage.value = "Running...";

  try {
    const result = await upsertBookmark(apiUrl.value, state);
    if (!result.response.ok) {
      const body = await result.response.json().catch(() => null);
      throw new Error(formatApiError(body, result.response.status));
    }

    responseMessageColor.value = "success";
    responseMessage.value = result.operation === "updated" ? "Updated" : "Registered";
  } catch (error) {
    responseMessageColor.value = "error";
    responseMessage.value = error instanceof Error ? error.message : String(error);
  } finally {
    pending.value = false;
  }
};

const remove = async () => {
  if (pending.value) return;

  pending.value = true;

  try {
    const url = new URL("/bookmarks", apiUrl.value);
    url.searchParams.set("url", state.url);
    const response = await fetch(url, {
      method: "DELETE",
    });

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(formatApiError(body, response.status));
    }

    responseMessageColor.value = "success";
    responseMessage.value = "Removed";
  } catch (error) {
    responseMessageColor.value = "error";
    responseMessage.value = error instanceof Error ? error.message : String(error);
  } finally {
    pending.value = false;
  }
};

const isGetFolderPending = ref(false);
const getFolders = async () => {
  if (pending.value && isGetFolderPending.value) return;

  isGetFolderPending.value = true;

  try {
    const response = await fetch(new URL("/folders", apiUrl.value));

    if (!response.ok) {
      throw new Error(String(await response.text()));
    }

    const folders = await response.json();
    folderItems.value = folders.map((e: { id: number; name: string }) => ({
      label: e.name,
      value: e.id,
    }));
  } catch (error) {
    responseMessageColor.value = "error";
    responseMessage.value = error instanceof Error ? error.message : String(error);
  } finally {
    isGetFolderPending.value = false;
  }
};

const isGetTags = ref(false);
const getTags = async () => {
  if (pending.value && isGetTags.value) return;

  isGetTags.value = true;

  try {
    const response = await fetch(new URL("/tags", apiUrl.value));

    if (!response.ok) {
      throw new Error(String(await response.text()));
    }

    const tags = await response.json();
    tagItems.value = tags.map((e: { id: number; name: string }) => ({
      label: e.name,
      value: e.id,
    }));
  } catch (error) {
    responseMessageColor.value = "error";
    responseMessage.value = error instanceof Error ? error.message : String(error);
  } finally {
    isGetTags.value = false;
  }
};

onMounted(async () => {
  const tab = await getActiveTab();

  if (tab?.title) {
    state.title = tab.title;
  }

  if (tab?.url) {
    state.url = tab.url;
  }

  await loadApiUrl();
  await connectApiServer();

  if (isApiServerConnect.value) {
    await loadExistingBookmark();
  }
});

watch(apiUrl, (value) => {
  void saveApiUrl(value);
});
</script>
