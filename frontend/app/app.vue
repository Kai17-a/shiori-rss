<template>
  <UApp>
    <NuxtLoadingIndicator />

    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>

<script setup lang="ts">
const colorMode = useColorMode();

const color = computed(() => {
  const mode = colorMode.value === "system" ? colorMode.preference : colorMode.value;
  return mode === "dark" ? "#1b1718" : "white";
});

useHead({
  meta: [
    { charset: "utf-8" },
    { name: "viewport", content: "width=device-width, initial-scale=1" },
    { key: "theme-color", name: "theme-color", content: color },
  ],
  link: [{ rel: "icon", href: "/favicon.ico" }],
  htmlAttrs: {
    lang: "ja",
  },
});

const title = "Shiori Keeper";
const description = "At-a-glance view of your bookmark system.";

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description,
});
</script>
