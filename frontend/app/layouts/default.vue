<template>
  <UDashboardGroup unit="rem">
    <UDashboardSidebar
      id="default"
      v-model:open="open"
      collapsible
      class="bg-elevated/25 lg:sticky lg:top-0 lg:h-dvh"
      :ui="{ footer: 'lg:border-t lg:border-default' }"
    >
      <template #header="{ collapsed, collapse }">
        <button
          type="button"
          class="flex w-full items-center px-1 py-2"
          aria-label="Expand sidebar"
          @click="collapse(false)"
        >
          <span v-if="!collapsed" class="min-w-0">
            <span class="block text-base font-semibold tracking-normal text-highlighted">Shiori Feed</span>
          </span>
          <UIcon v-else name="i-lucide-panel-left-open" class="size-5 text-muted" />
        </button>
      </template>
      <template #default="{ collapsed }">
        <SidebarNav
          :collapsed="collapsed"
          :primary-links="primaryLinks"
          :secondary-links="secondaryLinks"
          @navigate="closeSidebar"
        />
      </template>

    </UDashboardSidebar>

    <div
      v-if="healthChecked && !healthOk"
      class="fixed inset-x-4 top-4 z-50 ml-auto max-w-md lg:left-auto"
      role="status"
      aria-live="polite"
    >
      <UAlert
        title="API server is unavailable"
        description="Saved data cannot be loaded or changed until the connection is restored."
        icon="i-lucide-cloud-off"
        color="error"
        variant="subtle"
        orientation="vertical"
      >
        <template #actions>
          <UButton
            label="Retry connection"
            icon="i-lucide-refresh-cw"
            color="error"
            variant="soft"
            size="xs"
            :loading="healthChecking"
            loading-icon="i-lucide-loader-circle"
            @click="retryApiConnection"
          />
        </template>
      </UAlert>
    </div>

    <slot />
    <AskAIChatLauncher />
  </UDashboardGroup>
</template>
<script setup lang="ts">
import type { NavigationMenuItem } from "@nuxt/ui";
import AskAIChatLauncher from "~/components/AskAIChatLauncher.vue";
import { refreshSidebarCatalogSafely } from "~/utils/sidebarCatalog";

const route = useRoute();
const { refresh } = useSidebarCatalog();
const {
  checked: healthChecked,
  ok: healthOk,
  checking: healthChecking,
  check: checkApiHealth,
} = useApiHealth();
const toast = useSingleToast();

const open = ref(false);

const closeSidebar = () => {
  open.value = false;
};

const retryApiConnection = async () => {
  const reachable = await checkApiHealth(true);
  if (!reachable) return;

  await refreshSidebarCatalogSafely(refresh, true);
  toast.show({
    title: "API server connection restored.",
    color: "success",
    icon: "i-lucide-check",
  });
};

const isActive = (path: string) => route.path === path;
const isActivePrefix = (path: string) => route.path === path || route.path.startsWith(`${path}/`);

const primaryLinks = computed<NavigationMenuItem[]>(() => [
  {
    label: "Home",
    icon: "i-lucide-house",
    to: "/",
    active: isActive("/"),
    onSelect: closeSidebar,
  },
  {
    label: "IT trends",
    icon: "i-lucide-flame",
    to: "/trends",
    active: isActive("/trends"),
    onSelect: closeSidebar,
  },
  {
    label: "Articles",
    icon: "i-lucide-library-big",
    to: "/articles",
    active: isActive("/articles"),
    onSelect: closeSidebar,
  },
  {
    label: "RSS feeds",
    icon: "i-lucide-rss",
    to: "/feeds",
    active: isActivePrefix("/feeds"),
    onSelect: closeSidebar,
  },
  {
    label: "Custom RSS",
    icon: "i-lucide-wand-sparkles",
    to: "/custom-feeds",
    active: isActivePrefix("/custom-feeds"),
    onSelect: closeSidebar,
  },
]);

const secondaryLinks = computed<NavigationMenuItem[]>(() => [
  {
    label: "Docker images",
    icon: "i-lucide-container",
    to: "/docker-images",
    active: isActive("/docker-images"),
    onSelect: closeSidebar,
  },
  {
    label: "GitHub",
    icon: "i-lucide-github",
    to: "/github",
    active: isActive("/github"),
    onSelect: closeSidebar,
  },
  {
    label: "AI analysis data",
    icon: "i-lucide-database",
    to: "/ai-data",
    active: isActive("/ai-data"),
    onSelect: closeSidebar,
  },
  {
    label: "Preferences",
    icon: "i-lucide-sliders-horizontal",
    to: "/settings",
    active: isActive("/settings"),
    onSelect: closeSidebar,
  },
]);

onMounted(() => {
  void refreshSidebarCatalogSafely(refresh);

  window.setTimeout(() => {
    void (async () => {
      if (healthChecked.value) return;

      await checkApiHealth();
      toast.show({
        title: healthOk.value ? "API server is reachable." : "API server is unavailable.",
        color: healthOk.value ? "success" : "warning",
        icon: healthOk.value ? "i-lucide-check" : "i-lucide-circle-alert",
      });
    })();
  }, 1000);
});
</script>
