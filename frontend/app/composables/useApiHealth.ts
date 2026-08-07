import {
  createApiHealthState,
  requestApiHealth,
  type ApiHealthState,
} from "~/utils/apiHealth";

export const useApiHealth = () => {
  const state = useState<ApiHealthState>("api-health", createApiHealthState);
  const { request } = useApi();
  const checking = ref(false);
  let loadPromise: Promise<boolean> | null = null;

  const check = async (force = false) => {
    if (state.value.checked && !force) {
      return state.value.ok === true;
    }

    if (loadPromise) {
      return loadPromise;
    }

    loadPromise = (async () => {
      checking.value = true;
      try {
        state.value.ok = await requestApiHealth(request);
        state.value.checked = true;
        return state.value.ok === true;
      } finally {
        checking.value = false;
        loadPromise = null;
      }
    })();

    return loadPromise;
  };

  return {
    checked: computed(() => state.value.checked),
    ok: computed(() => state.value.ok),
    checking: computed(() => checking.value),
    check,
  };
};
