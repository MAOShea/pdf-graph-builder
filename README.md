# Knowledge Graph Builder
![Python](https://img.shields.io/badge/Python-yellow)
![FastAPI](https://img.shields.io/badge/FastAPI-green)
![React](https://img.shields.io/badge/React-blue)


Transform unstructured data (PDFs, DOCs, TXTs, YouTube videos, web pages, etc.) into a structured Knowledge Graph stored in Neo4j using the power of Large Language Models (LLMs) and the LangChain framework.

This application allows you to upload files from various sources (local machine, GCS, S3 bucket, or web sources), choose your preferred LLM model, and generate a Knowledge Graph.

## Getting Started

### **Prerequisites**
- **Python 3.12 or higher** (for local/separate backend deployment)
- Neo4j Database **5.23 or later** with APOC installed.
  - Neo4j 5.23 is required because the backend uses the Cypher variable-scope subquery syntax (`CALL (variable) { ... }`), which is not supported by earlier Neo4j 5.x releases such as 5.20.
  - **Neo4j Aura** databases (including the free tier) are supported.
  - If using **Neo4j Desktop**, you will need to deploy the backend and frontend separately (docker-compose is not supported).

#### **Backend Setup**
1. Create a `.env` file in the `backend` folder by copying `backend/example.env`.
2. Pre-configure user credentials in the `.env` file to bypass the login dialog:
   ```bash
   NEO4J_URI=<your-neo4j-uri>
   NEO4J_USERNAME=<your-username>
   NEO4J_PASSWORD=<your-password>
   NEO4J_DATABASE=<your-database-name>
   ```
3. Run:
   ```bash
   cd backend
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn score:app --reload
   ```


## Key Features

### **Knowledge Graph Creation**
- Seamlessly transform unstructured data into structured Knowledge Graphs using advanced LLMs.
- Extract nodes, relationships, and their properties to create structured graphs.

### **Schema Support**
- Use a custom schema or existing schemas configured in the settings to generate graphs.

### **Graph Visualization**
- View graphs for specific or multiple data sources simultaneously in **Neo4j Bloom**.

### **Chat with Data**
- Interact with your data in the Neo4j database through conversational queries.
- Retrieve metadata about the source of responses to your queries.
- For a dedicated chat interface, use the standalone chat application with the **[/chat-only](/chat-only) route.**

### **LLMs Supported**
1. OpenAI
2. Gemini
3. Diffbot
4. Azure OpenAI (dev deployed version)
5. Anthropic (dev deployed version)
6. Fireworks (dev deployed version)
7. Groq (dev deployed version)
8. Amazon Bedrock (dev deployed version)
9. Ollama (dev deployed version)
10. Deepseek (dev deployed version)
11. Other OpenAI-compatible base URL models (dev deployed version)


### **Token Usage Tracking**
- Easily monitor and track your LLM token usage for each user and database connection.
- Enable this feature by setting the `TRACK_USER_USAGE` environment variable to `true` in your backend configuration.
- View your daily and monthly token consumption and limits, helping you manage usage and avoid overages.
- You can check your remaining token limits at any time using the provided API endpoint.

### **Embedding Model Selection**
- Choose from a variety of embedding models to generate vector embeddings for your data. This can be configured from the frontend in **Graph Settings > Processing Configuration > Select Embedding Model**.
- Supported model providers include OpenAI, Gemini, Amazon Titan, and Sentence Transformers.
- Your selected embedding model is saved to your user profile when `TRACK_USER_USAGE` is enabled.

#### **Local Configuration**
You have two ways to configure the embedding model locally:

1.  **With User Tracking (`TRACK_USER_USAGE=true`):**
    - Set `TRACK_USER_USAGE` to `true` in your backend `.env` file.
    - Provide your token tracking database credentials (`TOKEN_TRACKER_DB_URI`, `TOKEN_TRACKER_DB_USERNAME`, etc.).
    - Select your desired embedding model from the frontend. Your selection will be saved and automatically used in subsequent sessions.

2.  **Without User Tracking (`TRACK_USER_USAGE=false`):**
    - Set `TRACK_USER_USAGE` to `false`.
    - Specify the embedding model and provider directly in your backend `.env` file using `EMBEDDING_MODEL` and `EMBEDDING_PROVIDER`.
    - If these variables are not set, the application defaults to a Sentence Transformer model.
    - In this mode, the embedding model cannot be changed from the frontend.


---

## Getting Started

### **Prerequisites**
- Neo4j Database **5.23 or later** with APOC installed.
  - Neo4j 5.23 is required because the backend uses the Cypher variable-scope subquery syntax (`CALL (variable) { ... }`), which is not supported by earlier Neo4j 5.x releases such as 5.20.
  - **Neo4j Aura** databases (including the free tier) are supported.
  - If using **Neo4j Desktop**, you will need to deploy the backend and frontend separately (docker-compose is not supported).

---

## Deployment Options

### **Local Deployment**

#### Using Docker-Compose
Run the application using the default `docker-compose` configuration.

1. **Supported LLM Models:**  
   By default, only OpenAI and Diffbot are enabled. Gemini requires additional GCP configurations.  
   Use the `VITE_LLM_MODELS_PROD` variable to configure the models you need. Example:
   ```bash
   VITE_LLM_MODELS_PROD="gemini_3.5_flash,openai_gpt_5.4_mini,diffbot,anthropic_claude_4.5_haiku"
   ```

2. **Anthropic Models:**
   Use the latest Claude model in your config:
   ```bash
   LLM_MODEL_CONFIG_ANTHROPIC_CLAUDE_4_7_OPUS="claude-opus-4-7,anthropic_api_key"
   ```

3. **Input Sources:**  
   By default, the following sources are enabled: `local`, `YouTube`, `Wikipedia`, `AWS S3`, and `web`.  
   To add Google Cloud Storage (GCS) integration, include `gcs` and your Google client ID:
   ```bash
   VITE_REACT_APP_SOURCES="local,youtube,wiki,s3,gcs,web"
   VITE_GOOGLE_CLIENT_ID="your-google-client-id"
   ```

#### Chat Modes
Configure chat modes using the `VITE_CHAT_MODES` variable:
- By default, all modes are enabled: `vector`, `graph_vector`, `graph`, `fulltext`, `graph_vector_fulltext`, `entity_vector`, and `global_vector`. 
- To specify specific modes, update the variable. For example:
  ```bash
  VITE_CHAT_MODES="vector,graph"
  ```

---

### **Running Backend and Frontend Separately**

For development, you can run the backend and frontend independently.

#### **Frontend Setup**
1. Create a `.env` file in the `frontend` folder by copying `frontend/example.env`.
2. Update environment variables as needed.
3. Run:
   ```bash
   cd frontend
  yarn
  yarn run dev
   ```

#### **Backend Setup**
1. Create a `.env` file in the `backend` folder by copying `backend/example.env`.
2. Pre-configure user credentials in the `.env` file to bypass the login dialog:
   ```bash
   NEO4J_URI=<your-neo4j-uri>
   NEO4J_USERNAME=<your-username>
   NEO4J_PASSWORD=<your-password>
   NEO4J_DATABASE=<your-database-name>
   ```
3. Run:
   ```bash
   cd backend
  python -m venv envName
  source envName/bin/activate
  pip install -r requirements.txt
  uvicorn score:app --reload
   ```

---

### **Cloud Deployment**

Deploy the application on **Google Cloud Platform** using the following commands:

#### **Frontend Deployment**
```bash
gcloud run deploy dev-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

#### **Backend Deployment**
```bash
gcloud run deploy dev-backend \
  --set-env-vars "OPENAI_API_KEY=<your-openai-api-key>" \
  --set-env-vars "DIFFBOT_API_KEY=<your-diffbot-api-key>" \
  --set-env-vars "NEO4J_URI=<your-neo4j-uri>" \
  --set-env-vars "NEO4J_USERNAME=<your-username>" \
  --set-env-vars "NEO4J_PASSWORD=<your-password>" \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

---

## For local llms (Ollama)
1. Pull the docker image of ollama
   ```bash
   docker pull ollama/ollama
   ```
2. Run the ollama docker image
   ```bash
   docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
   ```
3. Execute any llm model, e.g., llama3
   ```bash
   docker exec -it ollama ollama run llama3
   ```
4. Configure env variable in docker compose.
   ```env
   LLM_MODEL_CONFIG_ollama_<model_name>
   # example
   LLM_MODEL_CONFIG_ollama_llama3=${LLM_MODEL_CONFIG_ollama_llama3-llama3,http://host.docker.internal:11434}
   ```
5. Configure the backend API url
   ```env
   VITE_BACKEND_API_URL=${VITE_BACKEND_API_URL-backendurl}
   ```
6. Open the application in browser and select the ollama model for the extraction.
7. Enjoy Graph Building.
---

## Usage

### Use Case 1 — Bottom-up KG from scratch

The default mode. Point the tool at any unstructured source and let the LLM discover entities and relationships on its own.

1. **Connect** to your Neo4j instance — pass credentials via the backend `.env`, the login dialog, or drag-and-drop a Neo4j credentials file. AuraDB and AuraDS are both supported (indicated by the database / molecule icon respectively).
2. **Add sources** — choose from local files (PDF, DOCX, TXT), YouTube videos, Wikipedia pages, web URLs, AWS S3, or GCS buckets.
3. **Select a model** — pick the LLM from the dropdown. Use a cloud frontier model (OpenAI, Anthropic, Gemini) for best extraction quality, or [a local Ollama model](#for-local-llms-ollama) for fully private, cost-free operation.
4. **Optionally constrain the schema** — open *Graph Enhancement Settings → Entity Extraction* to define the node labels and relationship types you want extracted. Leave this blank for open-ended discovery.
5. **Generate the graph** — select one or more files with *New* status and click *Generate Graph*, or click it with no selection to process all queued files.
6. **Explore the result** — click *View* on a row to inspect the graph for that file, or select multiple files and click *Preview Graph* to see them overlaid. Three views are available: Lexical (document + chunks), Entity, and full Knowledge Graph.
7. **Chat with your data** — once extraction is complete, open the chatbot panel and ask questions. The response cites the source passages. Use the `/chat-only` route for a standalone chat interface.

---

### Use Case 2 — Scaffold-diff ingest (top-down, against a pre-built ontology)

Use this mode when a domain ontology or knowledge scaffold already exists in Neo4j (for example, one built by a companion bootstrap script). Instead of discovering schema from scratch, the tool **dresses up** the existing scaffold with evidence from the document — confirming claims, flagging contradictions, and marking concepts not yet in the scaffold for operator review.

This is the workflow used by **AI-DM-Assistant** to ingest TTRPG rulebook PDFs against a seed ontology of game mechanics.

#### Prerequisites

The target Neo4j database must already contain scaffold nodes. Scaffold nodes are identified by having a `tier` or `seed_id` property. Run the relevant bootstrap script against the database before starting ingest:

```bash
# Example from the AI-DM-Assistant companion repo
python schema/bootstrap.py --game mork-borg
```

#### Running the ingest

Call `POST /extract` with the standard parameters **plus** `ingest_mode=scaffold-diff`:

```bash
curl -X POST http://localhost:8000/extract \
  -F "file_name=MORK_BORG_BARE_BONES_EDITION.pdf" \
  -F "source_type=local file" \
  -F "model=ollama_llama3" \
  -F "ingest_mode=scaffold-diff" \
  -F "uri=bolt://localhost:7687" \
  -F "userName=neo4j" \
  -F "password=<password>" \
  -F "database=morkborg"
```

The backend will:

1. Read all scaffold nodes from the target database (nodes with `tier` or `seed_id` properties).
2. Inject the scaffold labels and seed IDs directly into the LLM extraction prompt, constraining it to the existing schema.
3. Classify every extracted concept against the scaffold:

| Signal | Written as | Meaning |
|---|---|---|
| `CONFIRMS_SEED` | `(Chunk)-[:CONFIRMS_SEED]->(SeedNode)` | PDF passage confirms a scaffold claim; node `coverage` upgraded to `ingest-confirmed` |
| `DOCUMENTED_BY` | `(Chunk)-[:DOCUMENTED_BY]->(SeedNode)` | Passage references this scaffold concept |
| `INSTANCE_OF` | `(ConcreteNode)-[:INSTANCE_OF]->(SeedNode)` | A concrete in-game value (e.g. a named weapon's damage die) |
| `OVERRIDES_SEED` | `(Chunk)-[:OVERRIDES_SEED]->(SeedNode)` | PDF passage contradicts the scaffold — flagged for operator review |
| `NEW_NODE` | `FlaggedConcept` node | Label not in scaffold — flagged, not added to schema |
| `NEW_REL` | `FlaggedRelationship` node | Relationship type not in scaffold — flagged, not added |

4. Never write `SPECIALIZES` (an ontological claim that belongs to the bootstrap phase only).
5. At the end of the run, propagate `coverage`: any scaffold node with at least one `CONFIRMS_SEED` edge is automatically upgraded from `research-only` to `ingest-confirmed`.

#### Reviewing the diff in Bloom

Import the perspective file into Neo4j Bloom to get a pre-configured diff view:

1. Open Neo4j Bloom and connect to the target database.
2. Go to **Perspectives → Import** and load `docs/bloom-scaffold-diff-perspective.json`.
3. Use the built-in **Saved Searches** to navigate the results:

| Saved search | What it shows |
|---|---|
| *All OVERRIDES_SEED (conflicts to review)* | Passages that contradict the scaffold |
| *Flagged NEW_NODE concepts* | Labels extracted from PDF but not in scaffold |
| *Flagged NEW_REL types* | Relationship types extracted but not in scaffold |
| *Seed nodes not yet confirmed by PDF* | Scaffold claims the PDF has not yet touched |
| *Seed nodes confirmed by PDF* | Scaffold claims backed by at least one passage |
| *Confirmed seeds with their evidence chunks* | Confirmed nodes with the passages that support them |

Node colours signal coverage state: **amber** = `research-only`, **green** = `ingest-confirmed`, **blue** = `operator-verified`. Set a node to `operator-verified` by editing its `coverage` property directly in Bloom once you have reviewed it.

---

## [ENV][env-sheet]
| Env Variable Name       | Mandatory/Optional | Default Value | Description                                                                                      |
|------------------------ |-------------------|---------------|--------------------------------------------------------------------------------------------------|
|                        |                   |               |                                                                                                  |
| **BACKEND ENV**         |                   |               |                                                                                                  |
| OPENAI_API_KEY          | Optional          |               | An OpenAI Key is required to use OpenAI LLM model to authenticate and track requests             |
| DIFFBOT_API_KEY         | Mandatory         |               | API key is required to use Diffbot's NLP service to extract entities and relationships from unstructured data |
| BUCKET_UPLOAD_FILE      | Optional          |               | Bucket name to store uploaded file on GCS                                                        |
| BUCKET_FAILED_FILE      | Optional          |               | Bucket name to store failed file on GCS while extraction                                         |
| USER_AGENT              | Optional          | llm-graph-builder | Name of the user agent to track Neo4j database activity                                      |
| ENABLE_USER_AGENT       | Optional          | true          | Boolean value to enable/disable Neo4j user agent                                                 |
| DUPLICATE_TEXT_DISTANCE | Optional          | 5             | This value is used to find distance for all node pairs in the graph and is calculated based on node properties |
| DUPLICATE_SCORE_VALUE   | Optional          | 0.97          | Node score value to match duplicate nodes                                                        |
| EFFECTIVE_SEARCH_RATIO  | Optional          | 1             | Ratio used for effective search calculations                                                     |
| GRAPH_CLEANUP_MODEL     | Optional          | openai_gpt_5_mini | Model name to clean up graph in post processing                                            |
| MAX_TOKEN_CHUNK_SIZE    | Optional          | 10000         | Maximum token size to process file content                                                       |
| YOUTUBE_TRANSCRIPT_PROXY| Mandatory         |               | Proxy key to process YouTube videos for getting transcripts                                      |
| IS_EMBEDDING           | Optional           | true          | Flag to enable text embedding                                                                    |
| KNN_MIN_SCORE          | Optional           | 0.8           | Minimum score for KNN algorithm                                                                  |
| GCP_LOG_METRICS_ENABLED| Optional           | False         | Flag to enable Google Cloud logs                                                                 |
| NEO4J_URI              | Optional           | neo4j://database:7687 | URI for Neo4j database                                                                  |
| NEO4J_USERNAME         | Optional           | neo4j         | Username for Neo4j database                                                                      |
| NEO4J_PASSWORD         | Optional           | password      | Password for Neo4j database                                                                      |                                               |
| GCS_FILE_CACHE         | Optional           | False         | If set to True, will save files to process into GCS. If False, will save files locally           |                   |
| ENTITY_EMBEDDING       | Optional           | False         | If set to True, it will add embeddings for each entity in the database                           |
| LLM_MODEL_CONFIG_ollama_<model_name> | Optional |           | Set ollama config as model_name,model_local_url for local deployments                            |
|                        |                   |               |                                                                                                  |
| **FRONTEND ENV**        |                   |               |                                                                                                  |
| VITE_BLOOM_URL         | Mandatory          | [Bloom URL][bloom-url] | URL for Bloom visualization                                |
| VITE_REACT_APP_SOURCES | Mandatory          | local,youtube,wiki,s3 | List of input sources that will be available                                 |
| VITE_CHAT_MODES        | Mandatory          | vector,graph+vector,graph,hybrid | Chat modes available for Q&A                                |
| VITE_ENV               | Mandatory          | DEV or PROD   | Environment variable for the app                                                                 |
| VITE_LLM_MODELS        | Optional           | openai_gpt_5_mini,gemini_flash_latest,anthropic_claude_4.5_haiku | Supported models for the application |
| VITE_BACKEND_API_URL   | Optional           | [localhost][backend-url] | URL for backend API                                        |
| VITE_TIME_PER_PAGE     | Optional           | 50            | Time per page for processing                                                                     |
| VITE_CHUNK_SIZE        | Optional           | 5242880       | Size of each chunk of file for upload                                                            |
| VITE_GOOGLE_CLIENT_ID  | Optional           |               | Client ID for Google authentication                                                              |
| VITE_LLM_MODELS_PROD   | Optional           | openai_gpt_5_mini,gemini_flash_latest,anthropic_claude_4.5_haiku | To distinguish models based on environment (PROD or DEV) |
| VITE_AUTH0_CLIENT_ID   | Mandatory if you are enabling Authentication otherwise it is optional |  | Okta OAuth Client ID for authentication |
| VITE_AUTH0_DOMAIN      | Mandatory if you are enabling Authentication otherwise it is optional |  | Okta OAuth Client Domain                                  |
| VITE_SKIP_AUTH         | Optional           | true          | Flag to skip authentication                                                                      |
| VITE_CHUNK_OVERLAP     | Optional           | 20            | Variable to configure chunk overlap                                                              |
| VITE_TOKENS_PER_CHUNK  | Optional           | 100           | Variable to configure tokens count per chunk. This gives flexibility for users who may require different chunk sizes for various tokenization tasks |
| VITE_CHUNK_TO_COMBINE  | Optional           | 1             | Variable to configure number of chunks to combine for parallel processing                        |

### Example Environment Files

Refer to the example environment files for additional variables and configuration:

- [Backend example.env](https://github.com/neo4j-labs/llm-graph-builder/blob/main/backend/example.env)
- [Frontend example.env](https://github.com/neo4j-labs/llm-graph-builder/blob/main/frontend/example.env)

---

## Cloud Build Deployment

You can deploy the backend and the frontend to Google Cloud Run using Cloud Build, either manually or via automated triggers.

### **Automated Deployment (Recommended)**
1. **Connect your repository to Google Cloud Build:**
   - In the Google Cloud Console, go to Cloud Build > Triggers.
   - Create a new trigger and select your repository.
   - Set the trigger to run on push to your desired branch (`main`, `staging`, or `dev`).
   - Cloud Build will automatically use the `cloudbuild.yaml` file in the root of your repository.

2. **Configure Substitutions and Secrets:**
   - In the trigger settings, add required substitutions (e.g., `_OPENAI_API_KEY`, `_DIFFBOT_API_KEY`, etc.) as environment variables or use Secret Manager for sensitive data.

3. **Push your code:**
   - When you push to the configured branch, Cloud Build will build and deploy your backend (and optionally frontend) to Cloud Run using the steps defined in `cloudbuild.yaml`.

### **Manual Deployment**
1. **Set up Google Cloud SDK and authenticate:**
   ```bash
   gcloud auth login
   gcloud config set project <YOUR_PROJECT_ID>
   ```

2. **Run Cloud Build manually:**
   ```bash
   gcloud builds submit --config cloudbuild.yaml \
     --substitutions=_REGION=us-central1,_REPO=cloud-run-repo,_OPENAI_API_KEY=<your-openai-key>,_DIFFBOT_API_KEY=<your-diffbot-key>,_BUCKET_UPLOAD_FILE=<your-bucket>,_BUCKET_FAILED_FILE=<your-bucket>,_PROJECT_ID=<your-project-id>,_GCS_FILE_CACHE=False,_TRACK_USER_USAGE=False,_TOKEN_TRACKER_DB_URI=...,_TOKEN_TRACKER_DB_USERNAME=...,_TOKEN_TRACKER_DB_PASSWORD=...,_TOKEN_TRACKER_DB_DATABASE=...,_DEFAULT_DIFFBOT_CHAT_MODEL=...,_YOUTUBE_TRANSCRIPT_PROXY=...,_EMBEDDING_MODEL=...,
       _EMBEDDING_PROVIDER=...,_BEDROCK_EMBEDDING_MODEL_KEY=...,_LLM_MODEL_CONFIG_OPENAI_GPT_5_2=...,_LLM_MODEL_CONFIG_OPENAI_GPT_5_MINI=...,_LLM_MODEL_CONFIG_GEMINI_2_5_FLASH=...,_LLM_MODEL_CONFIG_GEMINI_2_5_PRO=...,_LLM_MODEL_CONFIG_DIFFBOT=...,_LLM_MODEL_CONFIG_GROQ_LLAMA3_1_8B=...,_LLM_MODEL_CONFIG_ANTHROPIC_CLAUDE_4_5_SONNET=...,_LLM_MODEL_CONFIG_ANTHROPIC_CLAUDE_4_5_HAIKU=...,_LLM_MODEL_CONFIG_LLAMA4_MAVERICK=...,_LLM_MODEL_CONFIG_FIREWORKS_QWEN3_6=...,_LLM_MODEL_CONFIG_FIREWORKS_GPT_OSS=...,_LLM_MODEL_CONFIG_FIREWORKS_DEEPSEEK_V3=...,_LLM_MODEL_CONFIG_BEDROCK_NOVA_MICRO_V1=...,_LLM_MODEL_CONFIG_BEDROCK_NOVA_LITE_V1=...,_LLM_MODEL_CONFIG_BEDROCK_NOVA_PRO_V1=...,_LLM_MODEL_CONFIG_OLLAMA_LLAMA3=...
   ```
   - Replace the values in angle brackets with your actual configuration and secrets.
   - `LLM_MODEL_CONFIG_FIREWORKS_QWEN3_6` is the app-facing config key for the `fireworks_qwen3_6` model option and should map to the Fireworks serverless slug `accounts/fireworks/models/qwen3p6-plus`.
   - You can omit or add substitutions as needed for your deployment.

3. **Monitor the build:**
   - The build and deployment process will be visible in the Cloud Build console.

4. **Access your deployed service:**
   - After deployment, your backend will be available at the Cloud Run service URL shown in the Cloud Console.

---

**Note:**  
- The `cloudbuild.yaml` file supports multiple environments (`main`, `staging`, `dev`) based on the branch name.
- The frontend build and deployment steps are commented out by default. Uncomment them in `cloudbuild.yaml` if you wish to deploy the frontend as well.

For more details, see the comments in [`cloudbuild.yaml`](cloudbuild.yaml).

---

## Links

[LLM Knowledge Graph Builder Application][app-link]

[Neo4j Workspace][neo4j-workspace]

## Reference

[Demo of application][demo-video]

## Contact
For any inquiries or support, feel free to raise [GitHub Issues][github-issues]

[backend-url]: http://localhost:8000
[env-sheet]: https://docs.google.com/spreadsheets/d/1DBg3m3hz0PCZNqIjyYJsYALzdWwMlLah706Xvxt62Tk/edit?gid=184339012#gid=184339012
[env-vars]: https://docs.google.com/spreadsheets/d/1DBg3m3hz0PCZNqIjyYJsYALzdWwMlLah706Xvxt62Tk/edit?gid=0#gid=0
[app-link]: https://llm-graph-builder.neo4jlabs.com/
[neo4j-workspace]: https://workspace-preview.neo4j.io/workspace/query
[demo-video]: https://www.youtube.com/watch?v=LlNy5VmV290
[github-issues]: https://github.com/neo4j-labs/llm-graph-builder/issues
[bloom-url]: https://workspace-preview.neo4j.io/workspace/explore?connectURL={CONNECT_URL}&search=Show+me+a+graph&featureGenAISuggestions=true&featureGenAISuggestionsInternal=true
[langchain-endpoint]: https://api.smith.langchain.com

## Happy Graph Building!
