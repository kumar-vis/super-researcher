import { defineConfig } from "vite";

export default defineConfig({
  build: {
    outDir: "superresearcher/web/atlas",
    emptyOutDir: true,
    lib: {
      entry: "superresearcher/web/atlas-src/atlas.mjs",
      formats: ["es"],
      fileName: () => "atlas.js"
    },
    rollupOptions: {
      output: {
        assetFileNames: "atlas.[ext]"
      }
    }
  }
});
