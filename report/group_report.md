# Group Report — Day 10: Data Pipeline & Data Observability

> Báo cáo nhóm 2 thành viên. Các thông tin như tên nhóm, repository, họ tên và MSSV sẽ được thay bằng thông tin thực tế của nhóm trước khi nộp.

## 1. Thông tin bài nộp

| Thông tin       | Nội dung                                                   |
| --------------- | ---------------------------------------------------------- |
| Khóa/Lớp        | K3                                                         |
| Tên nhóm        | Flash                                                      |
| Repository      | https://github.com/zangzang1303/DAY10_DungSiDietChuot_D303 |
| Ngày hoàn thành | 2026-08-06                                                 |

### Thành viên và phân công

| STT | Họ và tên    | MSSV        | Vai trò chính                     | Module/deliverable sở hữu                                                                                                                               |
| --: | ------------ | ----------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
|   1 | Bùi Thọ An   | 2A202601183 | Data Pipeline Owner               | `src/crossref.py`, `src/cleaning.py`, `src/testset.py`, `data/raw/`, `data/clean/`, `data/eval/test_set.json`                                           |
|   2 | Lê Tuấn Cảnh | 2A202601127 | Observability & Integration Owner | `src/quality.py`, `src/reporting.py`, `src/corruption.py`, `src/phase1.py`, `src/corruption_flow.py`, `data/quality/`, `data/results/`, `data/reports/` |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Trong bài lab này, nhóm xây dựng một pipeline RAG hoàn chỉnh từ nguồn dữ liệu Crossref API, bao gồm các bước lấy dữ liệu thô, lưu raw artifacts, làm sạch dữ liệu, tạo dataset sạch, xây dựng evaluation set cố định, chạy embedding và retrieval bằng ChromaDB, sau đó đánh giá kết quả trả lời của hệ thống. Nhóm cũng triển khai các bước data observability để kiểm tra chất lượng dữ liệu, độ đầy đủ, tính hợp lệ và freshness của dataset.

Pipeline baseline tạo ra các artifact chính gồm dữ liệu thô trong `data/raw/`, dữ liệu sạch trong `data/clean/`, bộ câu hỏi đánh giá cố định trong `data/eval/test_set.json`, metrics trong `data/results/` và quality report trong `data/quality/`. Sau đó, nhóm thực hiện controlled corruption bằng cách làm hỏng một phần dữ liệu như xóa summary, làm stale published date hoặc làm thiếu dữ liệu quan trọng. Các corruption này được kỳ vọng làm giảm completeness, freshness và ảnh hưởng trực tiếp đến retrieval hit rate hoặc chất lượng câu trả lời RAG.

Bước repair được thực hiện bằng cách khôi phục lại dataset từ raw snapshot đã lưu, thay vì tự sửa thủ công kết quả lỗi. Giới hạn hiện tại của nhóm là số lượng thành viên chỉ có 2 người nên mỗi người phải phụ trách nhiều module, tuy nhiên nhóm vẫn giữ nguyên data contract và evaluation set để đảm bảo so sánh công bằng giữa baseline, corrupted và repaired.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối              | Input                            | Xử lý chính                                                                                           | Output/artifact                                      | Owner        |
| ----------------- | -------------------------------- | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------- | ------------ |
| Ingestion         | Crossref API                     | Fetch dữ liệu, retry khi lỗi, parse response thành records                                            | `data/raw/`                                          | Bùi Thọ An   |
| Cleaning          | Raw records                      | Chuẩn hóa title, summary, published date, authors, categories; tạo `text_for_embedding` và `age_days` | `data/clean/`                                        | Bùi Thọ An   |
| Embedding/index   | Clean dataset                    | Tạo embedding, build ChromaDB collection, lưu index/manifest                                          | `data/embeddings/` hoặc ChromaDB storage             | Lê Tuấn Cảnh |
| Evaluation        | Clean dataset + test set + index | Chạy retrieval, sinh câu trả lời, tính retrieval hit rate, token F1 hoặc judge score                  | `data/results/`                                      | Lê Tuấn Cảnh |
| Observability     | Clean/corrupted/repaired dataset | Kiểm tra completeness, validity, duplicates, freshness                                                | `data/quality/`                                      | Lê Tuấn Cảnh |
| Corruption/repair | Clean dataset + raw snapshot     | Gây lỗi có kiểm soát, repair từ raw artifacts, rebuild dataset/index                                  | `data/results/corruption_log.json`, repaired dataset | Lê Tuấn Cảnh |
| Orchestration     | Các module pipeline              | Chạy baseline, corrupted, repaired theo đúng thứ tự                                                   | Reports/metrics                                      | Lê Tuấn Cảnh |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng                                                            |
| ------------------------- | -------------------------------------------------------------------------- |
| `LLM_PROVIDER`            | `gemini`                                                                   |
| `LLM_MODEL`               | `gemini-2.5-flash`                                                         |
| `Embedding model`           | `sentence-transformers/all-MiniLM-L6-v2`                                   |
| Số lượng Crossref records | 24                                                                         |
| Retrieval `top_k`         | 4                                                                          |
| Freshness threshold       | 180 (ngày)                                                                 |
| Random seed, nếu có       | 42                                                                         |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

Nhóm sử dụng một trong hai cách sau.

Nếu dùng `uv`:

```bash
uv sync
```

Nếu dùng `pip`:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Nhóm không chỉ dùng `pip install -r requirements.txt` vì project cần được cài bằng editable mode để các import chéo trong package `src/` hoạt động đúng.

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh              | Trạng thái                              | Thời điểm chạy gần nhất | Bằng chứng                                                                                                       |
| ----------------- | --------------------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Baseline pipeline | Thành công                              | 2026-08-06              | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`                                            |
| Corruption flow   | Thành công                              | 2026-08-06              | `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính            | Giá trị                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------- |
| Source                | Crossref API                                                                                          |
| Query/filter          | `query="agentic retrieval augmented generation large language model"`, `filter="from-pub-date:180d,has-abstract:true"` |
| Thời điểm lấy dữ liệu | 2026-08-06                                                                                            |
| Số record nhận được   | 24                                                                                                    |
| Cơ chế retry/backoff  | Có retry khi request lỗi hoặc API trả lỗi tạm thời; giới hạn số lần retry theo cấu hình trong starter |

### Raw và clean schema

| Trường               | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa                                                                    | Xử lý khi thiếu/sai                                                                 |
| -------------------- | ------------ | --------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `paper_id`           | string       | Có        | ID duy nhất của paper, dùng để join với evaluation set và retrieval result | Loại record nếu không tạo được ID                                                   |
| `title`              | string       | Có        | Tiêu đề paper                                                              | Loại record hoặc đánh dấu invalid nếu thiếu                                         |
| `summary`            | string       | Không     | Abstract hoặc mô tả ngắn của paper                                         | Cho phép rỗng nhưng bị ghi nhận trong quality report                                |
| `published`          | string/date  | Không     | Ngày xuất bản đã chuẩn hóa                                                 | Gán unknown/null và tính freshness tương ứng                                        |
| `authors_joined`     | string       | Không     | Danh sách tác giả nối thành chuỗi                                          | Gán chuỗi rỗng nếu thiếu                                                            |
| `categories_joined`  | string       | Không     | Danh sách category/subject nối thành chuỗi                                 | Gán chuỗi rỗng nếu thiếu                                                            |
| `age_days`           | integer      | Không     | Số ngày từ ngày xuất bản đến thời điểm chạy pipeline                       | Gán null nếu không parse được ngày                                                  |
| `text_for_embedding` | string       | Có        | Văn bản tổng hợp dùng để embedding và retrieval                            | Tạo từ title, summary, authors, categories; nếu quá ngắn thì đánh dấu quality issue |
| `abs_url`            | string       | Không     | Link abstract hoặc DOI URL                                                 | Gán rỗng nếu thiếu                                                                  |
| `pdf_url`            | string       | Không     | Link PDF nếu có                                                            | Gán rỗng nếu thiếu                                                                  |

### Quy tắc cleaning

| Quy tắc                                      | Quality dimension liên quan | Số record bị tác động | Cách xác minh                                         |
| -------------------------------------------- | --------------------------- | --------------------: | ----------------------------------------------------- |
| Loại record không có `paper_id` hợp lệ       | Validity                    |                     0 | Kiểm tra `data/clean/` và quality report              |
| Loại hoặc đánh dấu record không có `title`   | Completeness                |                     0 | Kiểm tra missing title rate                           |
| Chuẩn hóa `summary` từ abstract/raw text     | Completeness/Validity       |                    24 | Kiểm tra missing summary rate                         |
| Chuẩn hóa ngày xuất bản `published`          | Freshness/Validity          |                    24 | Kiểm tra parse date và `age_days`                     |
| Tạo `text_for_embedding` từ các trường chính | Retrieval quality           |                    24 | Kiểm tra cột `text_for_embedding` trong clean dataset |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

`paper_id` được tạo từ DOI hoặc định danh ổn định của paper trong Crossref. Nếu DOI tồn tại, nhóm ưu tiên dùng DOI vì đây là ID phù hợp để đối chiếu giữa clean dataset, evaluation set và retrieval results. `text_for_embedding` được tạo bằng cách nối các trường quan trọng như title, summary, authors và categories để embedding có đủ ngữ cảnh nội dung. `age_days` được tính từ ngày `published` đến thời điểm chạy pipeline, giúp đánh giá freshness của dữ liệu. Nếu ngày xuất bản không parse được, record được đánh dấu là thiếu hoặc không xác định freshness.

## 6. Evaluation setup

| Thành phần                            | Cấu hình thực tế                                             |
| ------------------------------------- | ------------------------------------------------------------ |
| Số câu hỏi                            | 8                                                            |
| Các `question_type`                   | title, summary, author, category                             |
| Ground-truth document ID              | Lấy từ `paper_id` trong clean dataset                        |
| Embedding model                       | `sentence-transformers/all-MiniLM-L6-v2`                     |
| Vector store/collection               | ChromaDB collection (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k`                     | 4                                                            |
| LLM provider/model                    | `gemini` / `gemini-2.5-flash`                                |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`                                    |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Test set phải được giữ nguyên trong cả ba trạng thái để đảm bảo so sánh công bằng. Nếu mỗi trạng thái dùng một bộ câu hỏi khác nhau, nhóm sẽ không thể kết luận việc thay đổi metric là do corruption hay do độ khó của câu hỏi thay đổi. Vì vậy, `data/eval/test_set.json` được freeze sau khi tạo và dùng lại cho baseline, corrupted và repaired.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                        | Trạng thái | Ghi chú                      |
| ------------------------ | ---------------------------------------- | ---------- | ---------------------------- |
| Raw response/records     | `data/raw/`                              | Có         | Raw snapshot dùng cho repair |
| Cleaned dataset          | `data/clean/`                            | Có         | Dataset sau cleaning         |
| Embedding manifest/index | `data/embeddings/` và `data/chroma/`     | Có         | Index phục vụ retrieval      |
| Evaluation set           | `data/eval/test_set.json`                | Có         | Dùng chung cho 3 trạng thái  |
| Baseline metrics         | `data/results/baseline_metrics.json`     | Có         | Metrics ban đầu              |
| Quality/freshness        | `data/quality/`                          | Có         | Quality report baseline      |
| Baseline report          | `data/reports/phase1_report.md`          | Có         | Báo cáo baseline             |

### Baseline metrics

| Metric               |       Giá trị | Diễn giải                                                                 |
| -------------------- | ------------: | ------------------------------------------------------------------------- |
| `retrieval_hit_rate` |        1.0000 | Tỷ lệ câu hỏi mà top-k retrieval tìm đúng document ground truth           |
| `mean_token_f1`      |        0.2420 | Mức độ trùng khớp token giữa câu trả lời sinh ra và ground truth          |
| `judge_accuracy`     |        0.1250 | Tỷ lệ câu trả lời được LLM judge đánh giá là đúng                         |
| `mean_judge_score`   |        1.2500 | Điểm trung bình do LLM judge chấm                                         |
| Ragas, nếu có        |       Skipped | Bỏ qua Ragas pass nhanh; bật lại bằng `RUN_RAGAS=1`                       |

## 8. Data quality và freshness

### Quality checks

| Check                      | Quality dimension   | Ngưỡng/kỳ vọng       | Kết quả baseline      | Bằng chứng                                  |
| -------------------------- | ------------------- | -------------------- | --------------------- | ------------------------------------------- |
| Missing `paper_id`         | Validity            | 0%                   | PASS (0 missing, 0.0%) | `data/quality/baseline_quality_report.json` |
| Missing `title`            | Completeness        | Gần 0%               | PASS (0 missing, 0.0%) | `data/quality/baseline_quality_report.json` |
| Missing `summary`          | Completeness        | Dưới 20%             | PASS (0 missing, 0.0%) | `data/quality/baseline_quality_report.json` |
| Duplicate `paper_id`       | Uniqueness          | 0 duplicate          | PASS (0 duplicate, 0.0%)| `data/quality/baseline_quality_report.json` |
| Invalid `published`        | Validity/Freshness  | Dưới 50%             | PASS (0 invalid, 0.0%) | `data/quality/baseline_quality_report.json` |
| Empty `text_for_embedding` | Retrieval readiness | 0 hoặc rất thấp      | PASS (0 empty, 0.0%)  | `data/quality/baseline_quality_report.json` |

### Freshness

| Thuộc tính            | Giá trị                                                             |
| --------------------- | ------------------------------------------------------------------- |
| Freshness được đo tại | Clean dataset/index artifact                                        |
| Timestamp mới nhất    | 2026-08-01T00:00:00+00:00                                           |
| Ngưỡng freshness      | 180 (ngày)                                                          |
| Trạng thái baseline   | Fresh                                                               |
| Lý do                 | Dựa trên `published`, `age_days` và `stale_rows` = 0 (stale_rate = 0.0%) |

## 9. Corruption scenarios và repair

| Corruption                  | Cách tạo                                            | Record bị tác động | Quality signal kỳ vọng                                            | Tác động thực tế  | Cách repair                                    |
| --------------------------- | --------------------------------------------------- | -----------------: | ----------------------------------------------------------------- | ----------------- | ---------------------------------------------- |
| Missing summary corruption  | Xóa hoặc làm rỗng `summary` của 4 test-overlapping records |          4 | Missing summary rate tăng từ 0% lên 25.93% (vượt ngưỡng 20%)      | Token F1 sụt giảm từ 0.2420 xuống 0.1802 | Parse lại từ raw snapshot và chạy cleaning lại |
| Stale date corruption       | Sửa `published` thành 2000-01-01 cho 4 records      |          4 | Freshness giảm, `stale_rows` tăng từ 0 lên 4 (14.81%)             | Metadata ngày bị sai lệch | Khôi phục trường ngày từ raw records           |
| Noise injection corruption  | Thêm nhiễu ngẫu nhiên vào `text_for_embedding`      |          8 | Semantic quality của embedding bị giảm noise                     | Suy giảm độ chính xác trả lời | Rebuild `text_for_embedding` từ clean fields  |
| Duplicate corruption        | Nhân bản 3 records giữ nguyên `paper_id`            |          3 | Duplicate rate tăng lên 11.11%, vi phạm uniqueness constraint     | Duplicate rows trong index | Deduplicate khi cleaning lại từ raw            |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi rõ 4 loại corruption, 8 target paper IDs trùng với evaluation test set, 27 total corrupted rows và timestamp đầy đủ.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Repair được thực hiện bằng cách quay lại raw snapshot trong `data/raw/`, parse lại dữ liệu gốc, chạy lại cleaning, rebuild index và đánh giá lại trên cùng evaluation set. Cách này đảm bảo dữ liệu repaired không phải là kết quả sửa tay hoặc che lỗi ở tầng metrics, mà là phục hồi lại pipeline từ nguồn dữ liệu thô đã lưu. Vì test set được giữ nguyên, nhóm có thể đo được mức độ phục hồi một cách công bằng.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét                                                                |
| ------------------------ | -------: | --------: | -------: | ---------------------: | -----------: | ----------------------------------------------------------------------- |
| `retrieval_hit_rate`     |   1.0000 |    1.0000 |   1.0000 |                 0.0000 |       0.0000 | Top-k=4 vẫn tìm thấy document do title không bị hỏng                    |
| `mean_token_f1`          |   0.2420 |    0.1802 |   0.2420 |                -0.0618 |      +0.0618 | Blank summary & noise làm token F1 giảm 0.0618; repair phục hồi 100%    |
| `judge_accuracy`         |   0.1250 |    0.1250 |   0.1250 |                 0.0000 |       0.0000 | Tỷ lệ đánh giá chính xác của judge ổn định                              |
| `mean_judge_score`       |   1.2500 |    1.2500 |   1.2500 |                 0.0000 |       0.0000 | Điểm trung bình judge phản ánh kết quả sau retrieval                    |
| Quality checks pass/fail |     PASS |      FAIL |     PASS |      Fail 2 checks     |  Phục hồi PASS | Corrupted fail `paper_id_unique` và `summary_completeness`              |
| Freshness status         |    Fresh |     Fresh |    Fresh |    stale_rows +4       |  stale_rows 0 | Stale rows tăng từ 0 lên 4 ở corrupted, sau repair đưa về 0           |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. Missing summary corruption & Noise injection → Completeness signal bị suy giảm (missing summary rate 25.93%) và context bị gán nhiễu → `mean_token_f1` sụt giảm 0.0618 (từ 0.2420 xuống 0.1802).
2. Repair pipeline từ raw records → Completeness/freshness được khôi phục 100% (0 missing summary, 0 duplicate, 0 stale) → `mean_token_f1` phục hồi hoàn toàn về mức baseline 0.2420.

Không kết luận corruption “có tác động” nếu số liệu không cho thấy thay đổi. Nếu kết quả khác kỳ vọng, nhóm sẽ mô tả giả thuyết và kiểm tra lại artifact tương ứng.

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** Khi chạy lại `script/run_phase1.py` sau khi `script/run_corruption_flow.py` đã tạo các collection mới, ChromaDB ném ngoại lệ `chromadb.errors.NotFoundError: Error getting collection: Collection [UUID] does not exist` ở bước `index.search()`.
- **Nguyên nhân:** Phương thức `LocalEmbeddingIndex.build()` sử dụng `client.delete_collection()` để xóa collection cũ, làm vô hiệu hóa collection UUID handle trong bộ nhớ cache của Rust bindings thuộc `chromadb.PersistentClient`.
- **Cách xử lý:** Thay đổi cách làm mới index trong `LocalEmbeddingIndex.build()` bằng cách gọi `client.get_or_create_collection()` và xóa toàn bộ document IDs thông qua `collection.delete(ids=...)` thay vì xóa entity collection, đồng thời truyền trực tiếp collection & client instance vào constructor `cls(...)`.
- **Cách xác minh:** Chạy liên tiếp chuỗi lệnh `python script/run_phase1.py` và `python script/run_corruption_flow.py` thông suốt 100% không xuất hiện bất kỳ ngoại lệ ChromaDB nào.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại                                             | Ảnh hưởng                                                        | Hướng cải thiện có thể kiểm chứng                                       |
| ------------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Nhóm chỉ có 2 thành viên nên mỗi người phụ trách nhiều module | Dễ bị quá tải, khó review chéo toàn bộ code                      | Chia checklist rõ hơn và kiểm tra artifact sau từng bước                |
| Số lượng Crossref records có thể chưa lớn (24 records)        | Metrics có thể chưa phản ánh đầy đủ nhiều tình huống dữ liệu lỗi | Tăng số lượng records và chạy lại comparison                            |
| Corruption scenario còn tập trung ở summary & published date  | Chưa bao phủ hết các lỗi dữ liệu thực tế như malformed json/pdf  | Thêm scenario như invalid DOI, mixed schema hoặc stale index            |
| LLM judge phụ thuộc API key/provider                          | Có thể khó tái hiện nếu thiếu key hoặc quota                     | Bổ sung rule-based metrics như token F1 và retrieval hit rate           |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.

