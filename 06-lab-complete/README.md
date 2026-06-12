# Lab 12 - Complete Production RAG Agent

Dự án này productionize lại **Day08 RAG Pipeline** thành một API agent hoàn chỉnh, áp dụng các bước đã học trong Day 12: Docker, environment config, health check, readiness, API key authentication, rate limiting, cost guard, structured logging và deploy config.

## Dự Án Được Replace

Agent cá nhân/nhóm được dùng:

```text
Day08_RAG_pipeline_cohort2
```

Chức năng chính:

- Nhận câu hỏi từ user qua endpoint `POST /ask`.
- Truy xuất tài liệu từ dữ liệu RAG local trong `Day08_RAG_pipeline_cohort2/data`.
- Sinh câu trả lời tiếng Việt có citation.
- Nếu có `XAH_API_KEY`, agent dùng multi-agent generation.
- Nếu không có API key LLM, agent vẫn chạy offline bằng extractive fallback.

## Checklist Deliverable

- [x] Dockerfile multi-stage
- [x] docker-compose.yml gồm agent + redis
- [x] .dockerignore loại bỏ `.env`, `.git`, cache
- [x] Health check endpoint: `GET /health`
- [x] Readiness endpoint: `GET /ready`
- [x] API Key authentication bằng header `X-API-Key`
- [x] Rate limiting
- [x] Cost guard
- [x] Config từ environment variables
- [x] Structured JSON logging
- [x] Graceful shutdown
- [x] Railway config
- [x] Render config
- [ ] Public API URL sau khi deploy

## Cấu Trúc

```text
06-lab-complete/
├── app/
│   ├── main.py          # FastAPI production wrapper
│   ├── config.py        # 12-factor config
│   └── rag_agent.py     # Adapter gọi Day08 RAG pipeline
├── Day08_RAG_pipeline_cohort2/
│   ├── src/
│   │   └── task10_generation.py
│   └── data/
├── Dockerfile
├── docker-compose.yml
├── railway.toml
├── render.yaml
├── .env.example
├── .dockerignore
└── requirements.txt
```

## Chạy Local Bằng Python

Từ thư mục `06-lab-complete`:

```bash
cp .env.example .env.local
pip install -r requirements.txt
python -m app.main
```

PowerShell:

```powershell
Copy-Item .env.example .env.local
pip install -r requirements.txt
python -m app.main
```

Mở terminal khác và test:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Gọi RAG Agent:

```bash
curl -H "X-API-Key: dev-key-change-me-in-production" \
  -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Luật quy định thế nào về tàng trữ trái phép chất ma túy?"}'
```

PowerShell:

```powershell
curl -H "X-API-Key: dev-key-change-me-in-production" `
  -X POST http://localhost:8000/ask `
  -H "Content-Type: application/json" `
  -d '{"question":"Luật quy định thế nào về tàng trữ trái phép chất ma túy?"}'
```

## Chạy Bằng Docker Compose

Từ thư mục `06-lab-complete`:

```bash
cp .env.example .env.local
docker compose up --build
```

Test:

```bash
curl http://localhost:8000/health
curl -H "X-API-Key: dev-key-change-me-in-production" \
  -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Tin tức nào liên quan đến ma túy?"}'
```

## Environment Variables

Các biến quan trọng trong `.env.local` hoặc trên cloud:

```env
ENVIRONMENT=production
DEBUG=false
APP_NAME=Production RAG Agent
AGENT_API_KEY=your-secret-key
JWT_SECRET=your-jwt-secret
RATE_LIMIT_PER_MINUTE=20
DAILY_BUDGET_USD=5.0
XAH_API_KEY=
```

Ghi chú:

- `AGENT_API_KEY` bắt buộc đổi khi deploy production.
- `XAH_API_KEY` là optional. Nếu để trống, RAG Agent vẫn trả lời bằng fallback offline.
- Không commit `.env.local` hoặc `.env` lên Git.

## Deploy Railway

```bash
railway login
railway init
railway variables set ENVIRONMENT=production
railway variables set DEBUG=false
railway variables set APP_NAME="Production RAG Agent"
railway variables set AGENT_API_KEY=your-secret-key
railway variables set JWT_SECRET=your-jwt-secret
railway variables set XAH_API_KEY=your-xah-key
railway up
railway domain
```

Nếu không dùng LLM endpoint thật, có thể bỏ qua biến `XAH_API_KEY`.

## Deploy Render

1. Push repo lên GitHub.
2. Vào Render Dashboard.
3. Chọn **New -> Blueprint**.
4. Connect repo.
5. Render đọc file `render.yaml`.
6. Set secrets: `AGENT_API_KEY`, `JWT_SECRET`, optional `XAH_API_KEY`.
7. Deploy và lấy public URL.

## Public API URL

Sau khi deploy, điền URL thật vào đây:

```text
API URL: <chưa deploy>
Health: <chưa deploy>/health
Ask: POST <chưa deploy>/ask
```

Ví dụ request production:

```bash
curl -H "X-API-Key: your-secret-key" \
  -X POST https://your-app.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Luật quy định thế nào về tàng trữ trái phép chất ma túy?"}'
```

## Kiểm Tra Production Readiness

```bash
python check_production_ready.py
```

Script này kiểm tra các file và tính năng quan trọng trước khi nộp bài.
