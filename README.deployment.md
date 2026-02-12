# Deployment Plan (Cloud Run)

This is a simple, low‑ops deployment flow. Use Cloud Run to serve both the API and the UI from a single container.

## Prerequisites / sign‑ups

- **Google Cloud (Cloud Run)**: requires a GCP account and a billing‑enabled project *(even for free-tier deployment with limited trial period and credits).*
- **Artifact Registry (GCP)**: needed to deploy a prebuilt image to Cloud Run with `--image`.
- **Docker**: required to pull/run the prebuilt backend image locally *(optional to build image locally which needs `GUARDRAILS_API_KEY`).*
- **GHCR**: Recommended to pull prebuilt images from GitHub Container Registry *(optional to build image locally and publish to your own GHCR).*
- **Milvus (Zilliz Cloud)**: `MILVUS_URI` + `MILVUS_TOKEN` (Vector DB).  
- **OpenAI**: `OPENAI_API_KEY` for LLM calls.


## Backend: Cloud Run

1) **Create a GCP project** and enable billing.
    
    > **Quick links:** https://cloud.google.com/ → Click `Consol` → https://console.cloud.google.com/
    >
    > **Example project name:** sg-budget-rag
    >
    > **In the left menu:** Billing → Overview
    
2) **Enable Cloud Run** in the GCP console.
    > **In the left menu:** Cloud Run → Enable
3) **Recommended: pull the prebuilt image from GHCR**

    Fastest path for visitors to skip `DockerFile` fresh build image.

    ```bash
    # docker pull ghcr.io/<OWNER>/<REPO>:latest
    docker pull ghcr.io/phrey001/dataexpert-ai-capstone-sg-budget-rag:latest

    # Review Docker image list on local 
    docker image ls
    ```

    **(Optional) Local Docker Run Unit Test** 
    
    Excludes loading in relevant credentials like OPENAI_API_KEY, MILVUS_URI, MILVUS_TOKEN so the app won't work end-to-end like an integration test.

    ```bash
    # Troubleshooting Tips: May try another port from host:container if already used: e.g. 8081:8080

    # Recommended: if you pulled in already tagged prebuilt
    docker run --rm -p 8080:8080 ghcr.io/phrey001/dataexpert-ai-capstone-sg-budget-rag:latest

    # Alternative: if you have built and tagged it locally with `sg-budget-rag-backend` instead of pulling from GHCR (See below section: Optional Appendix)
    docker run --rm -p 8080:8080 sg-budget-rag-backend
    ```

4) **Google Cloud CLI Setup + gcloud authentication**

    ```bash
    # One-off google-cloud-cli installation: A warning to proceed is normal because Google Cloud CLI needs integration with systems that is not typical to normal snaps
    sudo snap install google-cloud-cli --classic

    # Proceed to authenticate with personal gmail after gcloud auth login
    gcloud auth login --no-launch-browser

    # Get project id from the billing-linked project on google cloud consol:
    #   Google Cloud Consol → Home → Project Info → Look for Project ID
    #
    #   Ignore the suggestion to add environment tag; Not needed for deployment
    #
    #   gcloud config set project <YOUR_PROJECT_ID>
    gcloud config set project sg-budget-rag
    ```


5) **Push Image to Google's Artifact Registry before deployment to Google Cloud Run**

    This step is needed because Google Cloud don't support running image directly from GHCR. So we use dual registry approach in this implementation to keep CICD architecture clean.

    Example:

    ```bash
    # GCP artifact registry path format
    #   <region>-docker.pkg.dev/<GCP_PROJECT_ID>/<GCP_ARTIFACTS_REPO>/<IMAGE_NAME>:latest

    # Add docker image tag
    #   docker tag <existing tag> <new tag>
    docker tag ghcr.io/phrey001/dataexpert-ai-capstone-sg-budget-rag:latest \
    asia-southeast1-docker.pkg.dev/sg-budget-rag/my-repo/sg-budget-rag-backend:latest

    # One-off create GCP artifacts repo if not exist
    #   gcloud artifacts repositories create <GCP_ARTIFACTS_REPO>
    gcloud artifacts repositories create my-repo \
    --repository-format=docker \
    --location=asia-southeast1 \
    --description="Docker repo for Cloud Run deployment"

    # Configures Docker to use gcloud as a credential helper (modifies Docker config file); “When Docker tries to push to this specific gcloud registry, ask gcloud for a token.”
    gcloud auth configure-docker asia-southeast1-docker.pkg.dev

    # push to Google Artifact Registry
    docker push asia-southeast1-docker.pkg.dev/sg-budget-rag/my-repo/sg-budget-rag-backend:latest
    ```

6) **Deploy to Cloud Run** (via console or CLI).  

    CLI example (gcloud):

    ```bash
    # gcloud run deploy <SERVICE_NAME>
    #   --image → tells Cloud Run to use image from Google Artifact Registry
    #   --allow-unauthenticated → public access for HTTP requests to this service
    #   --region asia-southeast1 → lower latency for users in region
    #   --platform managed → Managed (fully serverless); Simple deployment; NOT Cloud Run for Anthos (Kubernetes-based)
    #   --min-instances=0 → Allows idle to minimize billing
    #   --max-instances=1 → safe scaling cap; Never run more than one container (limit traffic)
    #   --cpu-throttling → Already default: free-tier friendly; CPU is allocated only during request handling (paused when no request)
    #   --memory → AI RAG backend requires a balance to not crash yet control cost
    gcloud run deploy sg-budget-rag \
      --image asia-southeast1-docker.pkg.dev/sg-budget-rag/my-repo/sg-budget-rag-backend:latest \
      --region asia-southeast1 \
      --platform managed \
      --allow-unauthenticated \
      --min-instances=0 \
      --max-instances=1 \
      --cpu-throttling \
      --memory=4Gi
    
    # (Optional) List deployed services on gcloud cli
    gcloud run services list

    # (Optional) Delete old service in deployment if not needed anymore 
    #   gcloud run services delete <OLD_SERVICE_NAME> --region <region>
    gcloud run services delete sg-budget-rag-backend --region asia-southeast1
    ```


7) **Set env vars** in Cloud Run (Web Browser):

    > Go to Google Cloud Console → Cloud Run → service `sg-budget-rag` →
    > “Edit & Deploy New Revision” → Variables & Secrets → Under Environment variables, click Add Variable

    - `OPENAI_API_KEY`
    - `MILVUS_URI`
    - `MILVUS_TOKEN`

    **Optional (LangSmith tracing)**

    > Copy these secrets from .env to cloudrun web platform if want to enable langsmith tracing for development/debugging. If enabled, Langsmith traces are reviewable at https://smith.langchain.com/

    - `LANGCHAIN_PROJECT`
    - `LANGCHAIN_TRACING_V2`
    - `LANGCHAIN_API_KEY`

    **Optional (similar name as when loading data into Milvus DB)**
    - `MILVUS_DB`
    
8) **Confirm the service URL**


## Notes

- Cloud Run can serve both the API and the UI from a single container.
- **Cost note:** Cloud Run is pay‑as‑you‑go (not free by default). It can be low‑cost for light traffic, but you should expect some billing once usage exceeds free quotas.

## (Optional) Appendix: Build + Publish to GitHub Container Registry (GHCR) as primary CI/CD registry

Visitors can skip this section unless they want to build/publish their own image.

Fresh build may take > 20-30 mins (heavy!).

```bash
# Load all env vars including GUARDRAILS_API_KEY, GITHUB_PAT from local .env
set -a
source .env
set +a

# Build and tag docker image (BuildKit secrets).
#   GUARDRAILS_API_KEY is used only during Docker build via BuildKit secrets to authenticate Guardrails Hub installs. It is NOT stored in the image.
#   This supports Guardrails being enabled by default at runtime.

# `docker build -t` here tags a local name
# `docker tag` here tags same image an extra tag, which we choose to include registry path which is needed for pushing to GHCR
DOCKER_BUILDKIT=1 docker build \
  --secret id=guardrails_key,env=GUARDRAILS_API_KEY \
  -t sg-budget-rag-backend .
# replace with visitor's personal OWNER/REPO variables
#   docker tag sg-budget-rag-backend ghcr.io/<OWNER>/<REPO>:latest
docker tag sg-budget-rag-backend ghcr.io/phrey001/dataexpert-ai-capstone-sg-budget-rag:latest

# Review that image is tagged successfuly; we would see 2 different image names pointing to same image id 
docker image ls

# Login (use a GitHub PAT with package:write)
#   replace with visitor's personal OWNER variables
#   echo $GITHUB_PAT | docker login ghcr.io -u <OWNER> --password-stdin
echo $GITHUB_PAT | docker login ghcr.io -u Phrey001 --password-stdin

# Push to GHCR
#   replace with visitor's personal OWNER/REPO variables
#   docker push ghcr.io/<OWNER>/<REPO>:latest
docker push ghcr.io/phrey001/dataexpert-ai-capstone-sg-budget-rag:latest
```

### GHCR package visibility for visitors

After first push, do once:

- GitHub → Profile → Packages → <REPO_NAME> → Settings → Public

Otherwise: `docker pull` will fail for vistors, and they’ll assume the image is broken.
