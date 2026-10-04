# AGENTS.md

## Bối cảnh
Repo này là một Enterprise RAG Knowledge Assistant: FastAPI, SQLAlchemy,
PostgreSQL 16 + pgvector, MinIO, Next.js, LLM và embedding qua API tương
thích OpenAI. Phần lớn code được sinh bằng AI và chủ repo chưa hiểu hết.
Đây là project học tập: mục tiêu là hiểu và chứng minh hiểu toàn bộ
pipeline RAG. Ưu tiên code đơn giản, dễ đọc, có đo lường, hơn là nhiều
tính năng.

## Mục tiêu
1. Đưa repo về trạng thái sạch, test và CI pass.
2. Giúp chủ repo hiểu code hiện tại, dọn phần thừa.
3. Nâng cấp lõi RAG: hỗ trợ PDF, embedding tốt hơn, hybrid search,
   reranker. Mỗi thay đổi đều đo bằng evaluation.
4. Sau khi phần lõi hoàn thành, mở rộng dần sang các bài toán nâng cao
   theo mục "Lộ trình sau".

## Quan hệ với tài liệu hiện có
Repo đã có docs/architecture.md (lộ trình Phase 1-10), docs/product.md,
docs/evaluation.md, docs/observability.md và các ADR trong docs/adr/.

- Thứ tự ưu tiên khi mâu thuẫn: AGENTS.md, rồi tới ADR mới nhất, rồi
  tới các tài liệu khác. Khi phát hiện mâu thuẫn thì báo, không tự chọn.
- Phase 1 và Phase 2 trong docs đã hoàn thành. AGENTS.md dùng từ
  "Giai đoạn" cho kế hoạch hiện tại, đối chiếu như sau:

  | AGENTS.md | docs/architecture.md |
  |---|---|
  | Giai đoạn 0-2 | Không có (ổn định, hiểu code, baseline) |
  | Giai đoạn 3 | Phase 3, chỉ phần PDF |
  | Giai đoạn 4-6 | Phase 4 |
  | Mục 7, 10, 11 | Phase 7 |
  | Mục 8 | Phase 8 |
  | Mục 9 (RBAC) | Chưa có, đang là non-goal trong product.md |
  | Mục 12 | Phase 9 |
  | Mục 13 | Phase 10, theo ADR-0009 và ADR-0010 |

  Phase 5 (observability hardening) và Phase 6 (multimodal) giữ nguyên
  trong docs, chưa nằm trong kế hoạch này.
- Không xóa hay sửa nội dung ADR cũ. Khi một quyết định thay đổi, viết
  ADR mới (đánh số tiếp từ 0012) ghi rõ "Supersedes ADR-xxxx", và đổi
  trạng thái ADR cũ thành "Superseded by ADR-yyyy".
- Các ADR sẽ bị thay thế: ADR-0003 ở Giai đoạn 3, ADR-0004 ở Giai đoạn
  5, và phần mặc định Ollama của ADR-0002 ở Giai đoạn 2.
- Sơ đồ: Mermaid trong docs/architecture.md là nguồn chính. Không sửa
  các file .excalidraw trong docs/diagrams/. Thêm ghi chú vào
  docs/diagrams/README.md rằng các sơ đồ đó có thể đã cũ.

## Giới hạn phần cứng
Máy phát triển: Windows 11, Intel i5-1135G7, 8GB RAM, không có GPU rời.
Mọi lựa chọn phải chạy được trong giới hạn này.
- Trên máy local, agent không tự khởi động frontend dev server và
  không build frontend vì giới hạn RAM; kiểm thử qua trang /docs của
  FastAPI. Chủ repo có thể tự chạy frontend khi muốn xem giao diện.
- Không chạy song song các tác vụ nặng (parse, embed, test).
- Trước khi thêm thư viện hay model mới, ước lượng RAM cần dùng và báo
  nếu vượt khoảng 1.5GB.
- Lệnh make và các script .sh chạy trong WSL2.

## Stack đích
- Giữ: FastAPI, SQLAlchemy, PostgreSQL + pgvector, lớp provider tương
  thích OpenAI.
- LLM mặc định: Gemini (key free tier từ Google AI Studio) qua endpoint
  tương thích OpenAI. Chỉ dùng cho bước sinh câu trả lời.
- LLM local: tùy chọn, model khoảng 1B tham số qua Ollama, chỉ để
  chứng minh đường local chạy được và để so sánh.
- Embedding: nomic-embed-text qua Ollama (768 chiều), chạy local.
- Parse PDF: Docling, chạy như một bước riêng và lưu kết quả ra đĩa.
- Keyword search: full-text search của Postgres, gộp với vector search
  bằng Reciprocal Rank Fusion (RRF).
- Reranker: cross-encoder nhỏ (ms-marco-MiniLM-L-6-v2), chạy CPU.
- Quan sát: log có cấu trúc bằng module logging chuẩn của Python.
- CI: GitHub Actions.

## Luồng xử lý một câu hỏi (trạng thái đích)
1. Nhận request POST /query.
2. Embed câu hỏi.
3. Tìm kiếm: vector search và keyword search, gộp bằng RRF.
4. Rerank bằng cross-encoder.
5. Kiểm tra ngưỡng bằng chứng. Không đủ thì từ chối, không gọi LLM.
6. Ghép context và prompt.
7. LLM sinh câu trả lời.
8. Trả về answer, cờ grounded và danh sách citation.

Sơ đồ này phải được vẽ bằng Mermaid trong docs/architecture.md, kèm
một sơ đồ riêng cho luồng ingest (parse, chunk, embed, index), và cập
nhật mỗi khi luồng thay đổi.

## Tài liệu tham khảo
Mỗi link chỉ dùng đúng phạm vi ghi bên dưới. Nếu không truy cập được
link nào thì báo lại, không tự đoán nội dung.

1. https://github.com/jamwithai/beginner-local-rag-system
   - Dùng để: lấy 3 file PDF mẫu trong thư mục notebooks/.
   - Không dùng: code, cấu hình, thư viện (PyPDF2, OpenSearch).

2. https://jamwithai.substack.com/p/the-infrastructure-that-powers-rag
   - Dùng để: tham khảo cách chia lớp routers / services /
     repositories khi refactor, và cách dùng Docling.
   - Không dùng: Airflow, OpenSearch, Langfuse.

3. https://github.com/langchain-ai/rag-from-scratch
   - Dùng để: tham khảo ý tưởng của các kỹ thuật (multi-query,
     RAG-Fusion, HyDE, routing, re-ranking) khi tới giai đoạn liên quan.
   - Không dùng: thư viện LangChain trước mục 11 của lộ trình sau. Mọi
     kỹ thuật phải được cài đặt bằng Python thuần trước.

## Không làm
- Không thêm LangChain, LangGraph, LlamaIndex trước mục 11 của lộ
  trình sau.
- Không thêm authentication, phân quyền, multi-turn chat, agent trước
  khi tới mục tương ứng trong lộ trình sau.
- Không thêm OpenSearch, Airflow, Langfuse.
- Không thêm OpenTelemetry, Jaeger, Prometheus, Grafana, Elasticsearch
  hay bất kỳ service giám sát nào.
- Không thêm bước tự đánh giá hay guardrail gọi LLM cho mỗi câu trả
  lời (tốn quota). Guardrail hiện có theo ADR-0008 giữ nguyên.
- Không sửa frontend/, infra/ và phần MinIO, trừ khi cần để test pass.
- Không triển khai lên cloud, không chạy terraform apply.
- Không tạo git tag, không kích hoạt release.
- Không commit file PDF, API key hay file .env vào repo. Không đưa API
  key lên GitHub Secrets.
- Không đưa tài liệu nội bộ công ty hay dữ liệu cá nhân vào repo hoặc
  vào corpus.
- Không bật billing cho Gemini. Chỉ dùng trong giới hạn free tier.
- Không dùng model local lớn hơn khoảng 1.5GB.

## Các giai đoạn (phần lõi)

### Giai đoạn 0 - Ổn định
- Kiểm tra môi trường: Docker Desktop, WSL2, Ollama, Python, uv. Ghi
  các bước khởi động chính xác vào README.
- Hướng dẫn giới hạn RAM cho WSL2 bằng file .wslconfig (memory=3GB).
- Tìm và sửa nguyên nhân pytest bị treo khi kết thúc.
- Tạo scripts/check.sh (xem mục "Sau mỗi lần build").
- Sửa .github/workflows/ci.yml theo mục "CI": giải thích thay đổi chưa
  commit (gỡ MinIO) ảnh hưởng tới test nào, đề xuất giữ hay revert, và
  cho workflow gọi scripts/check.sh.
- Kết quả: toàn bộ test pass trên máy local, tiến trình kết thúc bình
  thường, và CI pass.

### Giai đoạn 1 - Hiểu và lập kế hoạch (không sửa code)
- Đọc docs/architecture.md, docs/product.md, docs/evaluation.md,
  docs/observability.md và toàn bộ ADR. Báo những chỗ tài liệu không
  khớp với code thực tế.
- Đi theo một request POST /query và một lần ingest từ đầu đến cuối,
  giải thích từng file và hàm đi qua, kèm lý do thiết kế.
- Liệt kê code chết, logic trùng lặp, abstraction thừa, chỗ thiếu test,
  xếp theo mức độ rủi ro.
- Viết docs/refactor-plan.md: các bước refactor nhỏ, độc lập, không đổi
  hành vi. Thực hiện từng bước sau khi được duyệt.
- Được phép sửa tài liệu trong giai đoạn này: cập nhật phần lộ trình
  của docs/architecture.md theo bảng đối chiếu ở trên, và thêm hai sơ
  đồ Mermaid cho luồng hiện tại.

### Giai đoạn 2 - Gemini, logging và baseline evaluation
- Bước đầu tiên: tách cấu hình chat và embedding thành hai bộ độc lập;
  mỗi bộ có base_url, api_key và model riêng. Chat dùng Gemini, còn
  embedding tiếp tục dùng Ollama.
- Thêm Gemini làm provider LLM mặc định, chỉ bằng cấu hình, dùng lại
  lớp provider tương thích OpenAI:
  base_url = https://generativelanguage.googleapis.com/v1beta/openai/
  API key đọc từ biến môi trường GEMINI_API_KEY trong .env, thêm
  placeholder vào .env.example. Tên model đưa vào cấu hình, không
  hard-code.
- Viết ADR mới cho quyết định này: lý do là giới hạn phần cứng, đánh
  đổi là dữ liệu đi ra ngoài nên chỉ dùng tài liệu công khai.
- Thêm retry với backoff khi gặp lỗi 429.
- Logging: xem structured logging đang có trong answering.py và
  docs/observability.md trước, rồi mở rộng theo mục "Logging". Không
  viết một hệ logging thứ hai.
- Chạy evaluation harness hiện có (scripts/evaluate.py), lưu kết quả
  theo quy ước của docs/evaluation.md.
- Thêm chỉ số retrieval: hit rate@k và MRR, tính trên bộ câu hỏi có ghi
  rõ tài liệu và section chứa đáp án.
- Evaluation có tùy chọn chỉ chạy một phần bộ câu hỏi, và tùy chọn chỉ
  đo retrieval mà không gọi LLM, để tiết kiệm quota.
- Bộ câu hỏi do chủ repo viết tay. Không tự sinh câu hỏi hay đáp án.

### Giai đoạn 3 - PDF
- Viết ADR mới thay thế ADR-0003.
- Lấy dữ liệu mẫu: clone repo ở link tham khảo số 1 vào một thư mục
  tạm bên ngoài repo này, copy 3 file PDF trong notebooks/
  (attention is all you need.pdf, climate.pdf, ethical AI.pdf) vào
  data/papers/, rồi xóa thư mục tạm.
- Thêm data/papers/ và data/parsed/ vào .gitignore.
- Parse bằng Docling thành Markdown, lưu vào data/parsed/. Không parse
  lại nếu file gốc không đổi (so content hash).
- Chunk theo section cho PDF, bỏ phần References khỏi index. Giữ
  chunker hiện có cho Markdown/TXT.
- Mỗi chunk lưu metadata: tên tài liệu, section, số trang. Citation trả
  về các thông tin này.
- Cả hai đường ingest (CLI và upload qua API) phải dùng chung logic mới.
- Nếu Docling không chạy nổi trên máy này, báo lại và đề xuất phương án
  nhẹ hơn (ví dụ pymupdf4llm), không tự ý đổi.

### Giai đoạn 4 - Embedding
- Bỏ cố định Vector(384) trong models.py, đưa dimension vào cấu hình.
  Viết migration cho cột vector.
- Đổi sang nomic-embed-text (768 chiều), ingest lại toàn bộ. Model này
  cần prefix: "search_document: " cho chunk và "search_query: " cho
  câu hỏi.
- Hiệu chỉnh lại evidence threshold dựa trên dữ liệu đo được, không giữ
  nguyên 0.3.

### Giai đoạn 5 - Hybrid search
- Trước khi code: chủ repo bổ sung vài paper cùng chủ đề vào corpus và
  thêm câu hỏi tương ứng, rồi đo lại. Mục đích là có khoảng trống
  retrieval đo được, đúng tinh thần ADR-0004.
- Viết ADR mới thay thế ADR-0004, kèm số liệu đo trước khi thay đổi.
- Thêm full-text search của Postgres (cấu hình english), gộp với vector
  search bằng RRF.

### Giai đoạn 6 - Reranker và so sánh LLM
- Thêm bước rerank bằng cross-encoder nhỏ sau retrieval.
- Thêm một model local khoảng 1B qua Ollama làm provider thứ hai.
- Evaluation harness nhận tham số chọn provider, chạy cùng bộ câu hỏi
  trên cùng các chunk đã retrieve với cả hai LLM và xuất bảng so sánh.

## Lộ trình sau (chưa làm)
Chỉ bắt đầu khi Giai đoạn 0-6 đã hoàn thành và có số liệu evaluation.
Mỗi mục sẽ được chủ repo viết thành giai đoạn chi tiết khi tới lượt.
Không tự ý làm trước, không chuẩn bị sẵn code hay abstraction cho các
mục này.

7. RAG nâng cao: query rewriting, multi-query, HyDE. Mỗi kỹ thuật phải
   được đo bằng evaluation và chỉ giữ lại nếu cải thiện kết quả.
8. Multi-turn: lưu lịch sử hội thoại, viết lại câu hỏi nối tiếp thành
   câu hỏi độc lập trước khi retrieval.
9. Phân quyền (RBAC): user, role, quyền theo tài liệu. Lọc ngay ở tầng
   truy vấn Postgres. Phải có test chứng minh user không lấy được chunk
   của tài liệu mình không có quyền. Cần cập nhật non-goals trong
   docs/product.md và viết ADR.
10. Agent: routing giữa nhiều nguồn, tool calling, text-to-SQL cho dữ
    liệu dạng bảng. Viết bằng Python thuần trước.
11. Framework: viết lại phần agent bằng LangGraph trên nhánh riêng, giữ
    nguyên bản thuần, so sánh hai bản về số dòng code, độ dễ debug và
    kết quả evaluation.
12. Interoperability: mở retrieval thành MCP server để agent bên ngoài
    gọi được.
13. CD: CI build Docker image và đẩy lên GitHub Container Registry khi
    merge vào main. Triển khai thật lên cloud theo ADR-0009 và
    ADR-0010, chỉ làm khi chủ repo quyết định và đã ước lượng chi phí.

Lưu ý khi tới các mục này: multi-query và agent nhân số lần gọi LLM
cho mỗi câu hỏi, cần ước lượng quota Gemini trước khi làm.

## Logging
- Mỗi request /query có một request_id, gắn vào mọi dòng log của
  request đó.
- Mỗi bước (embed, search, rerank, generate) ghi một dòng log dạng
  JSON: tên bước, thời gian chạy tính bằng ms, và số liệu của bước đó
  (số chunk tìm được, số chunk sau rerank, số token vào/ra của LLM).
- Ghi thêm một dòng tổng kết cho request: tổng thời gian, grounded hay
  bị từ chối, provider và model đã dùng.
- Dùng module logging chuẩn của Python. Không log nội dung API key.
- Cập nhật docs/observability.md khi logging thay đổi.

## CI
- Workflow GitHub Actions chạy khi mở/cập nhật pull request và khi push
  lên nhánh main. Job
  backend chỉ gọi scripts/check.sh để CI và máy local chạy cùng một bộ
  lệnh backend (Ruff, mypy, pytest).
- Giữ nguyên job frontend tách riêng hiện có để lint/build frontend
  trên CI; job này không gọi scripts/check.sh. Agent không chạy các
  bước frontend đó trên máy local.
- Job Docker tách riêng chỉ build backend image để kiểm tra Dockerfile;
  không push image.
- Postgres (có pgvector) và MinIO chạy dạng service container trong CI.
- Test không được gọi API bên ngoài hay Ollama. LLM và embedding dùng
  provider giả trong test.
- Evaluation không chạy trong CI. Chạy trên máy local và commit kết quả
  theo quy ước của docs/evaluation.md.
- CI phải pass trước khi một giai đoạn được coi là hoàn thành.

## Sau mỗi lần build
Mỗi khi hoàn thành một thay đổi có code, phải làm đủ bốn việc sau
trước khi báo là xong:

1. Giải thích: đã build gì, vì sao làm theo cách đó, dữ liệu đi qua
   những file và hàm nào, và đánh đổi so với cách khác. Viết cho người
   đang học, không giả định đã biết.
2. Script kiểm tra: cập nhật scripts/check.sh để một lệnh duy nhất
   chạy được lint (Ruff), type check (mypy) và toàn bộ test (pytest).
   Từ Giai đoạn 2, thêm tùy chọn chạy evaluation. Script phải thoát với
   mã lỗi khác 0 khi có bước fail.
3. Hướng dẫn thử tay: đưa các lệnh cụ thể để chủ repo tự kiểm chứng
   tính năng vừa làm, ví dụ lệnh ingest và một lệnh curl gọi
   POST /query kèm kết quả mong đợi.
4. Cập nhật tài liệu: sửa docs/architecture.md (bảng component, mục
   Known constraints và hai sơ đồ Mermaid) cho khớp với code mới. Nếu
   cách chạy thay đổi thì sửa README. Quyết định thiết kế đáng kể thì
   viết ADR theo quy tắc ở mục "Quan hệ với tài liệu hiện có".

## Quy tắc làm việc
- Mỗi lần chỉ làm một giai đoạn, xong thì dừng và chờ duyệt.
- Trước khi sửa code, nêu ngắn gọn sẽ sửa file nào và vì sao.
- Commit nhỏ, mỗi commit một việc.
- Chạy scripts/check.sh sau mỗi thay đổi và báo kết quả thật. Nếu fail
  hoặc không chạy được thì nói rõ, không báo là đã xong.
- Từ Giai đoạn 3 trở đi, cuối mỗi giai đoạn chạy lại evaluation và so
  sánh với giai đoạn trước trong một bảng.
- Khi có nhiều cách làm, chọn cách đơn giản hơn và giải thích đánh đổi.
- Nếu thiếu thông tin thì hỏi, không tự đoán.
- Giải thích bằng tiếng Việt. Code, tên biến, commit message và tài
  liệu trong docs/ bằng tiếng Anh, theo đúng ngôn ngữ hiện có của repo.

## Trạng thái hiện tại
- Giai đoạn đang làm: 1
- Đã hoàn thành: Giai đoạn 0
