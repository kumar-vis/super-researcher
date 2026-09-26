import { defineConfig } from "vite";

export default defineConfig({
  build: {
    outDir: "web/atlas",
    emptyOutDir: true,
    lib: {
      entry: "web/atlas-src/atlas.mjs",
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
