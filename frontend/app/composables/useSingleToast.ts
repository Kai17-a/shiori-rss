export const useSingleToast = () => {
  const toast = useToast();

  const show = (next: Record<string, any>) => {
    toast.clear();
    return toast.add(next);
  };

  return {
    ...toast,
    show,
  };
};
