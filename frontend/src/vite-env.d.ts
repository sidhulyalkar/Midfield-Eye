/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MIDFIELDERS_EYE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
