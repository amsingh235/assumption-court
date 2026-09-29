# Deploy

Backend → Hugging Face Spaces (Docker, port 7860). Frontend → Vercel. Both need your own accounts; nothing here logs in for you.

## 1. Backend on Hugging Face Spaces

1. On https://huggingface.co/new-space create a Space: **SDK = Docker**, template **Blank**, hardware **CPU basic** (free).
   Note its name, e.g. `YOUR_USER/assumption-court-api`.
2. In the Space → **Settings → Variables and secrets**, add:

   | Name | Type | Value |
   |---|---|---|
   | `GEMINI_API_KEY` | Secret | your key from Google AI Studio |
   | `GEMINI_MODEL` | Variable | the current free-tier model name from the AI Studio docs |
   | `LLM_PROVIDER` | Variable | `gemini` |
   | `FRONTEND_ORIGIN` | Variable | your Vercel URL from step 2 (comma-separate several origins) |

3. Push the backend folder as the Space repo (from the repository root):

   ```bash
   git clone https://huggingface.co/spaces/YOUR_USER/assumption-court-api hf-space
   cp -r assumption-court/backend/{app,prompts,cached_cases,requirements.txt,Dockerfile,.dockerignore} hf-space/
   cp assumption-court/backend/SPACE_README.md hf-space/README.md    # Space config (sdk: docker, app_port: 7860)
   cd hf-space
   git add -A && git commit -m "Deploy Assumption Court API"
   git push                                                        # asks for your HF username + an access token (write)
   ```

4. Wait for the build, then check: `curl https://YOUR_USER-assumption-court-api.hf.space/health` → `{"ok":true}`.

To redeploy, repeat the `cp` + commit + push.

## 2. Frontend on Vercel

1. Push this repository to GitHub (if not already).
2. On https://vercel.com/new import the repository and set:
   - **Root Directory:** `assumption-court/frontend` (framework preset: Next.js, auto-detected)
   - **Environment variable:** `NEXT_PUBLIC_API_BASE` = `https://YOUR_USER-assumption-court-api.hf.space`
3. Deploy. Put the resulting URL (e.g. `https://assumption-court.vercel.app`) into the Space's `FRONTEND_ORIGIN` and restart the Space.

`NEXT_PUBLIC_*` values are baked in at build time, so redeploy the frontend after changing `NEXT_PUBLIC_API_BASE`.

## 3. Check

- Open the Vercel URL, replay an example (works even if the Space is asleep; examples are static in `frontend/public/examples/`).
- Start a live trial. If you see "Rate limit" you have used the 5 trials/hour per IP; if you see "quota exhausted", the Gemini free tier is spent for now.

## Local Docker test (optional)

```bash
cd assumption-court/backend
docker build -t assumption-court-api .
docker run --rm -p 7860:7860 -e LLM_PROVIDER=fake -e RETRIEVAL_PROVIDER=fake assumption-court-api
curl localhost:7860/health
```
