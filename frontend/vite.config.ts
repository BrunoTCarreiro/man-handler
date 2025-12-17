import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

// Check if network exposure is enabled via environment variable
const exposeNetwork = process.env.VITE_EXPOSE_NETWORK === "1" || 
                      process.env.VITE_EXPOSE_NETWORK === "true";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Only bind to 0.0.0.0 if network exposure is enabled, otherwise use localhost
    host: exposeNetwork ? "0.0.0.0" : "localhost",
  },
});


