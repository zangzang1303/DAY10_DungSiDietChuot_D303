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

| Khối              | Input                            | Xử lý chính                                                                                           | Output/artifact                                      | Owner                 |
| ----------------- | -------------------------------- | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------- | --------------------- |
| Ingestion         | Crossref API                     | Fetch dữ liệu, retry khi lỗi, parse response thành records                                            | `data/raw/`                                          | Bùi Thọ An            |
| Cleaning          | Raw records                      | Chuẩn hóa title, summary, published date, authors, categories; tạo `text_for_embedding` và `age_days` | `data/clean/`                                        | Bùi Thọ An            |
| Embedding/index   | Clean dataset                    | Tạo embedding, build ChromaDB collection, lưu index/manifest                                          | `data/embeddings/` hoặc ChromaDB storage             | Lê Tuấn Cảnh          |
| Evaluation        | Clean dataset + test set + index | Chạy retrieval, sinh câu trả lời, tính retrieval hit rate, token F1 hoặc judge score                  | `data/results/`                                      | [Họ tên thành viên 2] |
| Observability     | Clean/corrupted/repaired dataset | Kiểm tra completeness, validity, duplicates, freshness                                                | `data/quality/`                                      | Lê Tuấn Cảnh          |
| Corruption/repair | Clean dataset + raw snapshot     | Gây lỗi có kiểm soát, repair từ raw artifacts, rebuild dataset/index                                  | `data/results/corruption_log.json`, repaired dataset | Lê Tuấn Cảnh          |
| Orchestration     | Các module pipeline              | Chạy baseline, corrupted, repaired theo đúng thứ tự                                                   | Reports/metrics                                      | Lê Tuấn Cảnh          |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng                                                            |
| ------------------------- | -------------------------------------------------------------------------- |
| `LLM_PROVIDER`            | `gemini`                                                                   |
| `LLM_MODEL`               | `gemini-2.5-flash`                                                         |
| Embedding model           | `sentence-transformers/all-MiniLM-L6-v2` hoặc model mặc định trong starter |
| Số lượng Crossref records | [Điền số lượng thực tế sau khi chạy]                                       |
| Retrieval `top_k`         | [Điền giá trị thực tế, ví dụ: 3 hoặc 5]                                    |
| Freshness threshold       | [Điền ngưỡng thực tế trong code]                                           |
| Random seed, nếu có       | [Điền seed nếu có, ví dụ: 42]                                              |

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
| Baseline pipeline | [Thành công/Thất bại một phần/Thất bại] | 2026-08-06              | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`                                            |
| Corruption flow   | [Thành công/Thất bại một phần/Thất bại] | 2026-08-06              | `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/comparison_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính            | Giá trị                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------- |
| Source                | Crossref API                                                                                          |
| Query/filter          | [Query hoặc filter thực tế nhóm dùng]                                                                 |
| Thời điểm lấy dữ liệu | 2026-08-06                                                                                            |
| Số record nhận được   | [Số lượng thực tế]                                                                                    |
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
| Loại record không có `paper_id` hợp lệ       | Validity                    |            [Số lượng] | Kiểm tra `data/clean/` và quality report              |
| Loại hoặc đánh dấu record không có `title`   | Completeness                |            [Số lượng] | Kiểm tra missing title rate                           |
| Chuẩn hóa `summary` từ abstract/raw text     | Completeness/Validity       |            [Số lượng] | Kiểm tra missing summary rate                         |
| Chuẩn hóa ngày xuất bản `published`          | Freshness/Validity          |            [Số lượng] | Kiểm tra parse date và `age_days`                     |
| Tạo `text_for_embedding` từ các trường chính | Retrieval quality           |            [Số lượng] | Kiểm tra cột `text_for_embedding` trong clean dataset |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

`paper_id` được tạo từ DOI hoặc định danh ổn định của paper trong Crossref. Nếu DOI tồn tại, nhóm ưu tiên dùng DOI vì đây là ID phù hợp để đối chiếu giữa clean dataset, evaluation set và retrieval results. `text_for_embedding` được tạo bằng cách nối các trường quan trọng như title, summary, authors và categories để embedding có đủ ngữ cảnh nội dung. `age_days` được tính từ ngày `published` đến thời điểm chạy pipeline, giúp đánh giá freshness của dữ liệu. Nếu ngày xuất bản không parse được, record được đánh dấu là thiếu hoặc không xác định freshness.

## 6. Evaluation setup

| Thành phần                            | Cấu hình thực tế                                             |
| ------------------------------------- | ------------------------------------------------------------ |
| Số câu hỏi                            | [Số lượng thực tế]                                           |
| Các `question_type`                   | [Ví dụ: title, summary, author, category]                    |
| Ground-truth document ID              | Lấy từ `paper_id` trong clean dataset                        |
| Embedding model                       | `sentence-transformers/all-MiniLM-L6-v2` hoặc model mặc định |
| Vector store/collection               | ChromaDB collection theo cấu hình starter                    |
| Retrieval `top_k`                     | [Giá trị thực tế]                                            |
| LLM provider/model                    | `gemini` / `gemini-2.5-flash`                                |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`                                    |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Test set phải được giữ nguyên trong cả ba trạng thái để đảm bảo so sánh công bằng. Nếu mỗi trạng thái dùng một bộ câu hỏi khác nhau, nhóm sẽ không thể kết luận việc thay đổi metric là do corruption hay do độ khó của câu hỏi thay đổi. Vì vậy, `data/eval/test_set.json` được freeze sau khi tạo và dùng lại cho baseline, corrupted và repaired.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                        | Trạng thái | Ghi chú                      |
| ------------------------ | ---------------------------------------- | ---------- | ---------------------------- |
| Raw response/records     | `data/raw/`                              | [Có/Thiếu] | Raw snapshot dùng cho repair |
| Cleaned dataset          | `data/clean/`                            | [Có/Thiếu] | Dataset sau cleaning         |
| Embedding manifest/index | `data/embeddings/` hoặc ChromaDB storage | [Có/Thiếu] | Index phục vụ retrieval      |
| Evaluation set           | `data/eval/test_set.json`                | [Có/Thiếu] | Dùng chung cho 3 trạng thái  |
| Baseline metrics         | `data/results/baseline_metrics.json`     | [Có/Thiếu] | Metrics ban đầu              |
| Quality/freshness        | `data/quality/`                          | [Có/Thiếu] | Quality report baseline      |
| Baseline report          | `data/reports/phase1_report.md`          | [Có/Thiếu] | Báo cáo baseline             |

### Baseline metrics

| Metric               |       Giá trị | Diễn giải                                                                 |
| -------------------- | ------------: | ------------------------------------------------------------------------- |
| `retrieval_hit_rate` |     [Giá trị] | Tỷ lệ câu hỏi mà top-k retrieval tìm đúng document ground truth           |
| `mean_token_f1`      |     [Giá trị] | Mức độ trùng khớp token giữa câu trả lời sinh ra và ground truth          |
| `judge_accuracy`     |     [Giá trị] | Tỷ lệ câu trả lời được LLM judge đánh giá là đúng                         |
| `mean_judge_score`   |     [Giá trị] | Điểm trung bình do LLM judge chấm                                         |
| Ragas, nếu có        | [Giá trị/N/A] | Nếu không chạy Ragas, ghi rõ lý do không cấu hình hoặc ngoài phạm vi nhóm |

## 8. Data quality và freshness

### Quality checks

| Check                      | Quality dimension   | Ngưỡng/kỳ vọng       | Kết quả baseline      | Bằng chứng                                  |
| -------------------------- | ------------------- | -------------------- | --------------------- | ------------------------------------------- |
| Missing `paper_id`         | Validity            | 0%                   | [Pass/Fail + giá trị] | `data/quality/baseline_quality_report.json` |
| Missing `title`            | Completeness        | Gần 0%               | [Pass/Fail + giá trị] | `data/quality/baseline_quality_report.json` |
| Missing `summary`          | Completeness        | Dưới ngưỡng cấu hình | [Pass/Fail + giá trị] | `data/quality/baseline_quality_report.json` |
| Duplicate `paper_id`       | Uniqueness          | 0 duplicate          | [Pass/Fail + giá trị] | `data/quality/baseline_quality_report.json` |
| Invalid `published`        | Validity/Freshness  | Dưới ngưỡng cấu hình | [Pass/Fail + giá trị] | `data/quality/baseline_quality_report.json` |
| Empty `text_for_embedding` | Retrieval readiness | 0 hoặc rất thấp      | [Pass/Fail + giá trị] | `data/quality/baseline_quality_report.json` |

### Freshness

| Thuộc tính            | Giá trị                                                             |
| --------------------- | ------------------------------------------------------------------- |
| Freshness được đo tại | Clean dataset/index artifact                                        |
| Timestamp mới nhất    | [Giá trị]                                                           |
| Ngưỡng freshness      | [Giá trị]                                                           |
| Trạng thái baseline   | [Fresh/Stale/Unknown]                                               |
| Lý do                 | Dựa trên `published`, `age_days` và ngưỡng freshness trong cấu hình |

## 9. Corruption scenarios và repair

| Corruption                  | Cách tạo                                            | Record bị tác động | Quality signal kỳ vọng                                            | Tác động thực tế  | Cách repair                                    |
| --------------------------- | --------------------------------------------------- | -----------------: | ----------------------------------------------------------------- | ----------------- | ---------------------------------------------- |
| Missing summary corruption  | Xóa hoặc làm rỗng `summary` của một phần records    |         [Số lượng] | Missing summary rate tăng, `text_for_embedding` kém thông tin hơn | [Artifact/metric] | Parse lại từ raw snapshot và chạy cleaning lại |
| Stale date corruption       | Sửa `published` thành ngày cũ hơn hoặc không hợp lệ |         [Số lượng] | Freshness giảm, `age_days` tăng bất thường                        | [Artifact/metric] | Khôi phục trường ngày từ raw records           |
| Dropped document corruption | Xóa một số record liên quan đến evaluation set      |         [Số lượng] | Record count giảm, retrieval hit rate giảm                        | [Artifact/metric] | Rebuild clean dataset từ `data/raw/`           |
| Duplicate corruption        | Nhân bản một số record                              |         [Số lượng] | Duplicate rate tăng, uniqueness giảm                              | [Artifact/metric] | Deduplicate khi cleaning lại từ raw            |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: [Có/Thiếu]
- Nhận xét: Log cần ghi rõ loại corruption, số record bị tác động, tham số corruption và thời điểm chạy.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Repair được thực hiện bằng cách quay lại raw snapshot trong `data/raw/`, parse lại dữ liệu gốc, chạy lại cleaning, rebuild index và đánh giá lại trên cùng evaluation set. Cách này đảm bảo dữ liệu repaired không phải là kết quả sửa tay hoặc che lỗi ở tầng metrics, mà là phục hồi lại pipeline từ nguồn dữ liệu thô đã lưu. Vì test set được giữ nguyên, nhóm có thể đo được mức độ phục hồi một cách công bằng.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét                                                                |
| ------------------------ | -------: | --------: | -------: | ---------------------: | -----------: | ----------------------------------------------------------------------- |
| `retrieval_hit_rate`     |      [ ] |       [ ] |      [ ] |                    [ ] |          [ ] | Corruption có thể làm retrieval khó tìm đúng document hơn               |
| `mean_token_f1`          |      [ ] |       [ ] |      [ ] |                    [ ] |          [ ] | Câu trả lời có thể kém trùng khớp ground truth hơn khi dữ liệu bị thiếu |
| `judge_accuracy`         |      [ ] |       [ ] |      [ ] |                    [ ] |          [ ] | Nếu dùng LLM judge, corrupted có thể làm tỷ lệ đúng giảm                |
| `mean_judge_score`       |      [ ] |       [ ] |      [ ] |                    [ ] |          [ ] | Điểm trung bình phản ánh chất lượng answer sau retrieval                |
| Quality checks pass/fail |      [ ] |       [ ] |      [ ] |                    [ ] |          [ ] | Corruption kỳ vọng làm nhiều check fail hơn                             |
| Freshness status         |      [ ] |       [ ] |      [ ] |                    [ ] |          [ ] | Stale date corruption kỳ vọng làm freshness xấu đi                      |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. Missing summary corruption → completeness signal giảm và missing summary rate tăng → `text_for_embedding` thiếu thông tin → retrieval hoặc answer metric giảm.
2. Repair từ raw snapshot → completeness/freshness được phục hồi gần baseline → retrieval hit rate hoặc answer score tăng trở lại so với corrupted.

Không kết luận corruption “có tác động” nếu số liệu không cho thấy thay đổi. Nếu kết quả khác kỳ vọng, nhóm sẽ mô tả giả thuyết và kiểm tra lại artifact tương ứng.

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** [Ví dụ: evaluation không tìm thấy `ground_truth_doc_ids` trong retrieval result.]
- **Nguyên nhân:** [Ví dụ: `paper_id` trong clean dataset không khớp với ID trong test set.]
- **Cách xử lý:** [Ví dụ: thống nhất dùng DOI hoặc ID chuẩn hóa từ Crossref làm `paper_id`, sau đó regenerate/freeze lại test set.]
- **Cách xác minh:** [Ví dụ: chạy lại `python script/run_phase1.py` và kiểm tra `data/results/baseline_metrics.json`.]

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại                                             | Ảnh hưởng                                                        | Hướng cải thiện có thể kiểm chứng                                       |
| ------------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Nhóm chỉ có 2 thành viên nên mỗi người phụ trách nhiều module | Dễ bị quá tải, khó review chéo toàn bộ code                      | Chia checklist rõ hơn và kiểm tra artifact sau từng bước                |
| Số lượng Crossref records có thể chưa lớn                     | Metrics có thể chưa phản ánh đầy đủ nhiều tình huống dữ liệu lỗi | Tăng số lượng records và chạy lại comparison                            |
| Corruption scenario còn đơn giản                              | Chưa bao phủ hết các lỗi dữ liệu thực tế                         | Thêm scenario như duplicate, invalid DOI, mixed schema hoặc stale index |
| LLM judge phụ thuộc API key/provider                          | Có thể khó tái hiện nếu thiếu key hoặc quota                     | Bổ sung rule-based metrics như token F1 và retrieval hit rate           |

## 13. Checklist trước khi nộp

- [ ] Thông tin nhóm và repository chính xác.
- [ ] Phân công khớp với module, artifact và kết quả thực tế.
- [ ] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [ ] Baseline, corrupted và repaired dùng cùng evaluation set.
- [ ] Bảng metrics khớp với các file trong `data/results/`.
- [ ] Quality/freshness conclusions khớp với `data/quality/`.
- [ ] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [ ] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
