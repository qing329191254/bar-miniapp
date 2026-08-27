/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_TCB_ENV: string;
  readonly VITE_COS_PUBLIC_BASE: string;
  readonly VITE_COS_PREFIX: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<object, object, unknown>;
  export default component;
}
