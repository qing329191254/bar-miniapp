import { reactive } from "vue";

type ToastState = {
  visible: boolean;
  text: string;
  error: boolean;
};

const state = reactive<ToastState>({
  visible: false,
  text: "",
  error: false,
});

let timer: ReturnType<typeof setTimeout> | undefined;

export function useToastState() {
  return state;
}

export function showToast(text: string, error = false, duration?: number) {
  if (!text) return;
  if (timer) clearTimeout(timer);
  state.text = text;
  state.error = error;
  state.visible = true;
  const ms = duration ?? (error ? 3200 : 2200);
  timer = setTimeout(() => {
    state.visible = false;
  }, ms);
}

export function hideToast() {
  if (timer) clearTimeout(timer);
  state.visible = false;
}
