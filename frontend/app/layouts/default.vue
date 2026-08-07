<template>
  <UDashboardGroup unit="rem">
    <UDashboardSidebar
      id="default"
      v-model:open="open"
      collapsible
      class="bg-elevated/25 lg:sticky lg:top-0 lg:h-dvh"
      :ui="{ footer: 'lg:border-t lg:border-default' }"
    >
      <template #default="{ collapsed }">
        <SidebarNav
          :collapsed="collapsed"
          :primary-links="primaryLinks"
          :secondary-links="secondaryLinks"
          :primary-model-value="sidebarOpenItems"
          @navigate="closeSidebar"
        />
      </template>

      <template #footer="{ collapsed }">
        <div class="flex flex-col gap-2 w-full">
          <UButton
            :label="collapsed ? undefined : 'GitHub'"
            icon="i-simple-icons-github"
            color="neutral"
            variant="ghost"
            :block="collapsed"
            to="https://github.com/Kai17-a/browser-bookmark-manager"
            target="_blank"
          />

          <UButton
            :label="collapsed ? undefined : 'Extension'"
            icon="i-lucide-puzzle"
            color="neutral"
            variant="ghost"
            :block="collapsed"
            to="https://chrome.google.com/webstore/detail/dfjcocpbcdlleogghldbdcapomilohia"
            target="_blank"
          />
        </div>
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
            @click="retryApiConnection"
          />
        </template>
      </UAlert>
    </div>

    <slot />
  </UDashboardGroup>
</template>
<script setup lang="ts">
import type { NavigationMenuItem } from "@nuxt/ui";
import { refreshSidebarCatalogSafely } from "~/utils/sidebarCatalog";

const route = useRoute();
const { folders, tags, rssFeeds, newsSites, refresh } = useSidebarCatalog();
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
const sidebarOpenItems = computed(() => [
  ...(isActivePrefix("/folders") ? ["folders"] : []),
  ...(isActivePrefix("/tags") ? ["tags"] : []),
  ...(isActivePrefix("/rss") ? ["rss"] : []),
]);

const primaryLinks = computed<NavigationMenuItem[]>(() => [
  {
    label: "Dashboard",
    icon: "i-lucide-house",
    to: "/",
    active: isActive("/"),
    onSelect: closeSidebar,
  },
  {
    label: "Bookmarks",
    icon: "i-lucide-bookmark",
    to: "/bookmarks",
    active: isActivePrefix("/bookmarks"),
    onSelect: closeSidebar,
  },
  {
    label: "Favorites",
    icon: "i-lucide-star",
    to: "/favorites",
    active: isActive("/favorites"),
    onSelect: closeSidebar,
  },
  {
    label: "Folders",
    icon: "i-lucide-folder",
    to: "/folders",
    value: "folders",
    active: isActivePrefix("/folders"),
    defaultOpen: false,
    children: folders.value.map((folder) => ({
      label: folder.name,
      to: `/folders/${folder.id}`,
      exact: true,
      active: isActive(`/folders/${folder.id}`),
      onSelect: closeSidebar,
    })),
  },
  {
    label: "Tags",
    icon: "i-lucide-tag",
    to: "/tags",
    value: "tags",
    active: isActivePrefix("/tags"),
    defaultOpen: false,
    children: tags.value.map((tag) => ({
      label: tag.name,
      to: `/tags/${tag.id}`,
      exact: true,
      active: isActive(`/tags/${tag.id}`),
      onSelect: closeSidebar,
    })),
  },
  {
    label: "RSS",
    icon: "i-lucide-rss",
    to: "/rss",
    value: "rss",
    active: isActivePrefix("/rss"),
    defaultOpen: false,
    children: rssFeeds.value.map((feed) => ({
      label: feed.title,
      to: `/rss/${feed.id}`,
      exact: true,
      active: isActive(`/rss/${feed.id}`),
      onSelect: closeSidebar,
    })).concat(
      newsSites.value.map((site) => ({
        label: `Custom: ${site.title}`,
        to: `/rss/news/${site.id}`,
        exact: true,
        active: isActive(`/rss/news/${site.id}`),
        onSelect: closeSidebar,
      })),
    ),
  },
]);

const secondaryLinks = computed<NavigationMenuItem[]>(() => [
  {
    label: "Settings",
    icon: "i-lucide-settings",
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
