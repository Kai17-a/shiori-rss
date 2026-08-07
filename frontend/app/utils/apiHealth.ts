export type ApiHealthState = {
  checked: boolean;
  ok: boolean | null;
};

export const createApiHealthState = (): ApiHealthState => ({
  checked: false,
  ok: null,
});

export const requestApiHealth = async (
  request: <T>(path: string) => Promise<T>,
): Promise<boolean> => {
  try {
    const body = await request<{ status?: string }>("/health");
    return body?.status === "ok";
  } catch {
    return false;
  }
};
