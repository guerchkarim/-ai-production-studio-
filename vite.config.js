import {defineConfig} from 'vite';
export default defineConfig({root:'apps/web',server:{port:5174,strictPort:true,proxy:{'/api':process.env.STUDIO_API_URL || 'http://127.0.0.1:8001'}},build:{outDir:'../../dist',emptyOutDir:true}});
