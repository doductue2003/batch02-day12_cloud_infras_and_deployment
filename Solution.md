# Solution.md - Đáp án codelab 01 -> 05

## 01 - Localhost vs Production

### Vấn đề của bản develop

Ứng dụng trong `01-localhost-vs-production/develop` chạy được trên máy local nhưng chưa sẵn sàng production vì:

- API key/secrets bị hardcode trong source code.
- Port, debug mode và config bị cố định trong code.
- Không có endpoint `/health` để platform kiểm tra container còn sống hay không.
- Không xử lý graceful shutdown khi nhận `SIGTERM`.
- Logging còn đơn giản, khó quan sát khi deploy thật.

### Đáp án production

Phiên bản đúng nằm trong `01-localhost-vs-production/production`:

- Đọc config từ environment variable, thông qua `config.py`.
- Dùng `.env.example` làm template, không commit file `.env` thật.
- Thêm health check endpoint.
- Lấy `PORT`, `ENVIRONMENT`, `OPENAI_API_KEY` từ môi trường.
- Dùng structured logging thay vì chỉ `print`.
- Xử lý shutdown gọn gàng để request đang chạy có thời gian hoàn tất.

Lệnh chạy:

```bash
cd 01-localhost-vs-production/production
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Kiểm tra:

```bash
curl http://localhost:8000/health
```

### Câu hỏi thảo luận

1. Nếu push API key hardcode lên GitHub public, key có thể bị crawler quét được gần như ngay lập tức. Hậu quả là mất tiền do bị gọi API trái phép, lộ dữ liệu, bị khóa tài khoản hoặc phải rotate tất cả secrets liên quan.

2. Stateless quan trọng khi scale vì request của cùng một user có thể đi vào bất kỳ instance nào. Nếu state nằm trong memory của một instance, các instance khác sẽ không thấy session/conversation history, gây lỗi logic.

3. Dev/prod parity nghĩa là môi trường dev, staging và production càng giống nhau càng tốt: cùng cách config bằng env vars, cùng dependency, cùng container/runtime, cùng cách start app. Mục tiêu là giảm lỗi "it works on my machine".

## 02 - Docker

### Đáp án basic Dockerfile

Phiên bản develop đóng gói app vào container bằng Dockerfile đơn giản:

```bash
docker build -f 02-docker/develop/Dockerfile -t agent-develop .
docker run -p 8000:8000 agent-develop
curl http://localhost:8000/health
```

Docker giúp đóng gói runtime, dependency và command start app vào một image để chạy nhất quán trên mọi máy.

### Đáp án production Docker + Compose

Phiên bản production dùng multi-stage Dockerfile và Docker Compose:

- Builder stage cài dependency.
- Runtime stage chỉ copy phần cần thiết để chạy.
- Image nhỏ hơn, ít attack surface hơn.
- Compose chạy cả agent, Redis/vector store và Nginx reverse proxy.

Lệnh chạy:

```bash
docker compose -f 02-docker/production/docker-compose.yml up
docker compose -f 02-docker/production/docker-compose.yml ps
curl http://localhost/health
docker compose -f 02-docker/production/docker-compose.yml down
```

### Câu hỏi thảo luận

1. Nên `COPY requirements.txt .` và `RUN pip install` trước `COPY . .` để Docker cache layer cài dependency. Khi chỉ sửa source code, Docker không cần cài lại package, build nhanh hơn.

2. `.dockerignore` nên chứa `.git/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `.env`, log files và các file local không cần trong image. `venv/` làm build context rất nặng; `.env` có thể làm lộ secrets.

3. Nếu agent cần đọc file từ disk, mount volume vào container:

```bash
docker run -p 8000:8000 -v "$(pwd)/data:/app/data" agent-develop
```

Trong Docker Compose:

```yaml
volumes:
  - ./data:/app/data
```

## 03 - Cloud Deployment Options

### Chọn platform

Ba mức platform:

- Railway/Render: phù hợp MVP, demo, học tập; deploy nhanh trong vài phút.
- Cloud Run/AWS ECS: phù hợp production, có autoscaling, logging, IAM, CI/CD tốt hơn.
- Kubernetes: phù hợp enterprise/large-scale, cần nhiều service, traffic phức tạp, yêu cầu vận hành cao.

### Đáp án Railway

Railway phù hợp khi cần deploy nhanh:

```bash
railway login
railway init
railway up
```

Kết quả nhận URL dạng:

```text
https://your-app.up.railway.app
```

### Đáp án Render

Render dùng `render.yaml` để khai báo infrastructure as code: service, build command, start command, env vars và disk. Lợi ích là cấu hình deploy được version control trong Git.

### Đáp án Cloud Run

Cloud Run phù hợp production vì:

- Chạy container.
- Tự động scale.
- Có health check, revision, traffic splitting.
- Tích hợp Cloud Build qua `cloudbuild.yaml`.
- Service được khai báo bằng `service.yaml`.

### Câu hỏi thảo luận

1. Serverless Lambda không phải lúc nào cũng tốt cho AI agent vì agent có thể cần thời gian xử lý lâu, kết nối streaming, cache/model warm, background task, hoặc session/context dài. Lambda có timeout, cold start và giới hạn runtime.

2. Cold start là độ trễ khi platform phải khởi tạo instance mới trước khi xử lý request đầu tiên. Với AI agent, cold start làm UX chậm, request đầu tiên có thể timeout hoặc người dùng cảm thấy app "bị đứng".

3. Nên nâng từ Railway lên Cloud Run khi cần production reliability: autoscaling rõ ràng, IAM/secrets tốt hơn, CI/CD chuẩn, observability, traffic splitting, custom VPC, quản lý chi phí và SLA cao hơn.

## 04 - API Gateway & Security

### Đáp án basic API key

Phiên bản basic bảo vệ endpoint bằng header `X-API-Key`:

```bash
cd 04-api-gateway/develop
pip install -r requirements.txt
AGENT_API_KEY=my-secret-key python app.py
```

Request hợp lệ:

```bash
curl -H "X-API-Key: my-secret-key" \
  -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"hello"}'
```

Request không có key sẽ bị trả về `401 Unauthorized`.

### Đáp án production security stack

Phiên bản production gồm:

- `auth.py`: cấp và verify JWT.
- `rate_limiter.py`: giới hạn số request.
- `cost_guard.py`: bảo vệ ngân sách/token.
- `app.py`: ghép các lớp bảo vệ trước khi gọi agent.

Thứ tự xử lý:

```text
Request -> Auth -> Rate limit -> Input validation -> Cost check -> Agent
```

Lệnh chạy:

```bash
cd 04-api-gateway/production
pip install -r requirements.txt
python app.py
```

Lấy token:

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"student","password":"demo123"}'
```

Dùng token:

```bash
curl -H "Authorization: Bearer <token>" \
  -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"what is docker?"}'
```

### Câu hỏi thảo luận

1. API Key phù hợp service-to-service hoặc demo nội bộ. JWT phù hợp user login, có identity và expiry. OAuth2 phù hợp khi tích hợp bên thứ ba, delegated access, enterprise SSO.

2. Rate limit nên dựa trên chi phí và use case. Với demo có thể đặt 10-20 requests/phút/user. Production nên có nhiều lớp: per user, per IP, per org và daily/monthly budget.

3. Nếu API key bị lộ: revoke key ngay, rotate key mới, kiểm tra log để xác định mức độ bị lạm dụng, thêm alert bất thường, quét Git history, cập nhật secret store và thông báo các bên liên quan nếu có rủi ro dữ liệu.

## 05 - Scaling & Reliability

### Đáp án basic reliability

Phiên bản `05-scaling-reliability/develop/app.py` thêm các tính năng tối thiểu trước khi deploy:

- `GET /health`: liveness probe, cho biết app còn sống.
- `GET /ready`: readiness probe, cho biết app sẵn sàng nhận traffic.
- Biến `_is_ready`: đánh dấu trạng thái startup/shutdown.
- Biến `_in_flight_requests`: đếm request đang xử lý.
- Lifespan startup/shutdown: khi shutdown thì dừng nhận request mới và cho request đang chạy hoàn tất tối đa 30 giây.
- Bắt `SIGTERM`/`SIGINT` để log và để Uvicorn shutdown đúng cách.

Lệnh chạy:

```bash
cd 05-scaling-reliability/develop
pip install -r requirements.txt
python app.py
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### Đáp án advanced stateless scaling

Phiên bản `05-scaling-reliability/production/app.py` biến agent thành stateless:

- Session/conversation history không lưu trong memory của app instance.
- State được lưu trong Redis bằng key `session:<session_id>`.
- Mỗi request gửi `session_id` để tiếp tục hội thoại.
- Bất kỳ instance nào cũng đọc được session từ Redis.
- Nếu Redis không có, app fallback sang in-memory store, nhưng cách này không phù hợp scale.

Docker Compose production gồm:

- Nhiều `agent` instances.
- Redis làm shared session store.
- Nginx làm load balancer ở port `8080`.
- Healthcheck cho agent và Redis.

Lệnh chạy:

```bash
cd 05-scaling-reliability/production
docker compose up --scale agent=3
python test_stateless.py
```

Lưu ý: trong repo hiện tại, `docker-compose.yml` của lab 05 đang khai báo `dockerfile: 05-scaling-reliability/advanced/Dockerfile`, nhưng thư mục thực tế là `production`. Nếu chạy compose bị lỗi không tìm thấy Dockerfile, cần sửa đường dẫn này về Dockerfile production tương ứng trước khi build.

Kiểm tra bằng response:

- `served_by` có thể thay đổi qua từng request, chứng tỏ request được route sang instance khác nhau.
- `session_id` giữ nguyên.
- `/chat/{session_id}/history` vẫn có đầy đủ lịch sử, chứng tỏ state nằm trong Redis.

### Câu hỏi thảo luận

1. Liveness khác readiness: liveness trả lời "process còn sống không"; readiness trả lời "instance đã sẵn sàng nhận traffic chưa". Instance có thể live nhưng not ready, vì đang startup, đang shutdown hoặc mất dependency.

2. Load balancer cần readiness để không gửi traffic vào instance chưa load xong model, đang shutdown hoặc mất Redis/database. Nếu chỉ dùng liveness, user có thể gặp lỗi 503/timeout.

3. Redis giúp stateless scaling vì tách state ra khỏi memory của từng instance. Khi scale lên nhiều replicas, request vào instance nào cũng đọc/ghi được session chung.

4. Graceful shutdown quan trọng vì cloud platform thường gửi `SIGTERM` trước khi dừng container. Nếu app tắt đột ngột, request đang xử lý có thể bị mất, response lỗi và dữ liệu session chưa kịp lưu.

5. Để production tốt hơn, nên thêm metrics, distributed tracing, centralized logs, alert khi Redis lỗi, retry/backoff khi gọi LLM, request timeout, circuit breaker và persistent storage nếu session cần tồn tại lâu.

## Tóm tắt hoàn thành

Năm codelab đã cover đầy đủ các bước productionization cho AI agent:

- Config/secrets bằng environment variable.
- Container hóa bằng Docker.
- Chọn platform cloud theo mức độ sẵn sàng production.
- Bảo vệ API bằng auth, rate limit và cost guard.
- Scale reliable bằng health checks, graceful shutdown, Redis session và load balancing.
