FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

# NEXT_PUBLIC_* vars are inlined into the client bundle at `next build` time, not read at
# container runtime — Terraform's env{} block on the Cloud Run service (modules/cloud_run_web)
# sets NEXT_PUBLIC_API_BASE_URL for the *running* container, which `gcloud run deploy --source`
# never sees during the Cloud Build image build, so the client fell back to next.config's
# nothing / the code's own localhost:8000 default and every fetch from the deployed dashboard
# hit ERR_CONNECTION_REFUSED — confirmed live, not assumed. `gcloud run deploy --source` has no
# --build-arg flag for Dockerfile-based builds, so the fix is a build-time default here, not
# deploy-tooling plumbing — same "hardcode the known-stable value, document why" pattern as
# config.py's GCP_PROJECT_ID/FIRESTORE_PROJECT_ID.
FROM node:22-slim AS build
WORKDIR /app
ARG NEXT_PUBLIC_API_BASE_URL=https://prudently-api-jnpvbtwpwa-uc.a.run.app
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
# Firebase web config is designed to be public by Google's own model (it identifies the
# project, it doesn't authorize anything on its own) — same ARG/ENV pair pattern as
# NEXT_PUBLIC_API_BASE_URL above, for the identical build-time-vs-runtime reason. Defaults
# match src/lib/auth/firebase-client.ts's own fallback values.
ARG NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSyAv71Sf18UXwwt1BH0kWtx4VmaBNFwkI4A
ARG NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=prudently-hackathon.firebaseapp.com
ARG NEXT_PUBLIC_FIREBASE_PROJECT_ID=prudently-hackathon
ARG NEXT_PUBLIC_FIREBASE_APP_ID=1:439570031916:web:5b263c08f9ba2493abb889
ENV NEXT_PUBLIC_FIREBASE_API_KEY=$NEXT_PUBLIC_FIREBASE_API_KEY
ENV NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=$NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
ENV NEXT_PUBLIC_FIREBASE_PROJECT_ID=$NEXT_PUBLIC_FIREBASE_PROJECT_ID
ENV NEXT_PUBLIC_FIREBASE_APP_ID=$NEXT_PUBLIC_FIREBASE_APP_ID
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-slim AS run
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public

ENV PORT=8080
EXPOSE 8080
CMD ["node", "server.js"]
