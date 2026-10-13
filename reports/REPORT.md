# Lab 25B — Report

**Họ tên / nhóm:** Nguyen Quang Tuan / 02470  **Commit:** ba036a9  **Điểm tự động (`make grade`):** 84 / 88 (4 điểm SLO hidden do giảng viên chấm)

## 1. Kết quả Game Day

| Băng | Client | availability | p95 (s) | amplification | retry_ratio | cost/turn | recovery (s) | PASS? |
|---|---|---:|---:|---:|---:|---:|---:|:---:|
| G1 | naive | 0.7194 | 7.157 | 7.738 | 6.738 | 2.163 | 4 | Không |
| G1 | resilient | 1.0000 | 4.780 | 1.063 | 0.001 | 2.104 | 0 | Có |
| G2 | naive | 0.4560 | 15.034 | 9.904 | 8.904 | 4.627 | 155 | Không |
| G2 | resilient | 1.0000 | 10.362 | 1.036 | 0.005 | 2.108 | 0 | Có |
| G3 | naive | 1.0000 | 4.768 | 1.164 | 0.164 | 2.328 | 0 | Không |
| G3 | resilient | 1.0000 | 4.668 | 1.059 | 0.030 | 2.143 | 0 | Có |
| G4 | naive | 1.0000 | 13.764 | 1.004 | 0.004 | 2.008 | 0 | Không |
| G4 | resilient | 1.0000 | 5.626 | 1.014 | 0.002 | 2.072 | 0 | Có |
| G5 | naive | 0.3699 | 5.359 | 17.030 | 16.030 | 2.124 | – | Không |
| G5 | resilient | 0.8179 | 5.477 | 1.003 | 0.002 | 2.504 | – | Có |
| G6 | naive | 0.5170 | 4.836 | 12.344 | 11.344 | 2.009 | 0 | Không |
| G6 | resilient | 1.0000 | 6.025 | 1.056 | 0.019 | 2.188 | 0 | Có |

## 2. Cấu hình client và lý do

| Tham số | Giá trị | Lý do |
|---|---:|---|
| attempt_timeout_s | 8 s | Chừa đủ thời gian cho failover trong deadline 30 s; G6 vẫn đạt 100% availability. |
| max_attempts_per_provider | 2 | Chỉ một retry cùng provider; G3 retry ratio 0.030, dưới 0.10. |
| backoff base / cap | 0.25 / 4 s | Full jitter giảm đồng pha; G1 có 0 retry-after violation. |
| retry budget ratio | 0.10 | Hạn chế retry storm; G2 amplification 1.036. |
| breaker window / min calls | 20 / 10 | Có đủ mẫu trước khi mở breaker. |
| failure / slow threshold | 0.50 / 0.60 | Nhận biết lỗi thật và slow success; G4 p95 còn 5.626 s. |
| open duration / probes | 10 s / 2 | Probe giới hạn khi hồi phục; G2 recovery là 0 s. |

| Lỗi | Breaker | Hành động |
|---|---|---|
| 400/4xx client | release | GiveUp, không retry/failover |
| 429 quota | release | cooldown 300 s, failover |
| 429 rate limit | release | cooldown theo retry-after, failover |
| 500/503/529/timeout | failure | retry cùng provider nếu còn budget, nếu không failover |

## 3. Ba thí nghiệm

Kết quả thô của các lượt chạy bonus được lưu ở `reports/bonus.json`; chúng dùng client/control tạm và không thay đổi cấu hình nộp chính.

1. **Retry budget là lớp phòng thủ cuối.** Tôi tắt hiệu lực breaker (`min_calls=10^9`) và tăng lên 5 attempt/provider. Với budget, G2 có amplification 1.383, retry ratio 0.058, availability 0.9987 và recovery 0 s; bỏ budget thì các số lần lượt là 1.591, 0.382, 0.9725 và 22 s. Ở G3, việc không có budget làm tải/failover tích lũy đến availability 0.4235, trong khi có budget là 0.9984. Breaker là lớp phát hiện sức khoẻ provider; budget vẫn cần thiết để giới hạn thiệt hại khi breaker cấu hình sai, chậm phản ứng, hoặc nhận tín hiệu không hoàn hảo.
2. **`attempt_timeout_s: 30`.** Với G4, 8 s và 30 s gần như tương đương: availability đều 1.0, p95 lần lượt 5.626 và 5.683 s vì alpha vẫn trả lời và slow breaker đã chuyển tải. Với G6, lượt control 30 s vẫn đạt 1.0 availability và p95 5.425 s (8 s là 6.025 s) do phần lớn lỗi là 503 nhanh và breaker né region treo. Vì vậy không đánh giá timeout chỉ bằng p95: p95 bỏ qua lượt thất bại; timeout hợp lý phải xuất phát từ p99 bình thường, deadline người dùng, và vẫn chừa thời gian cho ít nhất một failover.
3. **Bỏ capability filter ở `ladder()`.** Control G6 gửi 453 attempt sang `gamma-mini`; 252 tool call không tương thích, `incompatible_routes=252`, availability giảm từ 1.0 xuống 0.8943. Theo góc nhìn product: khách được chuyển sang một nhân viên không biết dùng hệ thống hoàn tiền, nên 252 yêu cầu không thể hoàn tất dù vẫn còn model trả lời chat.

## 4. Workflow hoàn tiền

| Executor | completion | crashes | duplicate refunds | duplicate emails | lost refunds | overpaid | wasted LLM / crash |
|---|---:|---:|---:|---:|---:|---:|---:|
| naive | 1.0000 | 81 | 128 | 81 | 0 | 1,496,700 | 1.123 |
| yours | 1.0000 | 66 | 0 | 0 | 0 | 0 | 0.303 |

Idempotency key ngăn effect payment/email chạy hai lần sau timeout hoặc crash, nhưng không tránh tính lại các bước trước đó. Checkpoint tránh tính lại sau restart, nhưng một crash sau payment và trước checkpoint vẫn cần idempotency key. Ghi checkpoint trước payment có thể đánh dấu payment đã xong dù effect chưa xảy ra, dẫn tới mất tiền hoàn.

## 5. Alerting & error budget

Burn-rate alerter tạo 3 page, 1 ticket và 0 false page. Checkout bug/page được phát hiện sau 27 phút, provider outage/page sau 4 phút, slow leak/ticket sau 1,337 phút; deploy blip, night spike và small bump không page. Error budget 30 ngày: 55,618/129,508.8 bad request, đã tiêu 42.95%, còn 57.05%; chưa freeze release. `small_bump` không đánh thức on-call vì cả cửa sổ dài và ngắn không cùng vượt burn-rate page.

## 6. Postmortem — G2 với client naive (blameless)

**Tóm tắt:** G2 làm naive client chỉ đạt availability 45.60%, với amplification 9.904 và recovery 155 s. Trigger là alpha mất 75% GPU tại t=120; nguyên nhân gốc là ba tầng retry cố định, không budget/breaker, khuếch đại tải vào hàng đợi. Đây là vấn đề thiết kế hệ thống, không phải lỗi của một cá nhân.

**Ảnh hưởng:** 1,285/2,362 lượt user thất bại. Nếu chỉ sự cố này xảy ra trong tháng, 54.4% lượt lỗi vượt error budget 0.5% của tháng khoảng 108.8 lần.

| t | Sự kiện | Bằng chứng từ CSV |
|---:|---|---|
| 120 | Mất GPU bắt đầu | 7/7 call còn thành công, 5 attempt alpha/s. |
| 137 | Retry storm hình thành | 0/0 call thành công, 82 attempt alpha/s. |
| 141 | Hàng đợi bị bão hòa | 0/0 call thành công, 228 attempt/s. |
| 143 | Đỉnh tải retry | 0/0 call thành công, 254 attempt/s. |
| 300 | Provider hồi phục | 0/5 call thành công, vẫn 115 attempt/s. |
| 305 | Retry giảm nhưng backlog còn | 0/0 call thành công, 2 attempt/s. |
| 453 | Hệ thống mới hồi phục rõ | 4/8 call thành công, 7 attempt/s. |
| 468 | Phục hồi ổn định | 15/16 call thành công, 12 attempt/s. |

Provider không tự hồi phục sau t=300 vì queue còn đầy request mà client đã timeout/bỏ đi; retry tiếp tục tạo tải lớn hơn năng lực xử lý, nên failure tạo retry và retry lại tạo failure. Bản resilient cắt vòng lặp này: G2 đạt 100% availability, amplification 1.036 và recovery 0 s.

| # | Hành động | Loại | Owner | Cách kiểm chứng |
|---|---|---|---|---|
| 1 | Giữ retry một tầng với full jitter và budget | prevent | Agent platform | CI: G2 amplification ≤ 1.6 |
| 2 | Theo dõi amplification, queue wait và retry-after violations | detect | SRE | Alert khi amplification > 1.6 trong 5 phút |
| 3 | Sliding-window breaker, half-open tối đa 2 probe | mitigate | Runtime team | CI: G2 recovery ≤ 30 s |

## 7. Một điểm yếu còn lại

Khi mọi provider đồng thời chậm nhưng chưa lỗi, fallback không thể tạo thêm năng lực và chi phí có thể tăng khi beta gánh tải. Cần thêm admission control/load shedding theo tenant và đặt timeout theo baseline p99 cộng đủ thời gian cho một lần failover.

## 8. Cache

| Client | availability | faq_availability | cache_hit_ratio | stale_served | wrong_answers | outdated_answers | cost/turn | PASS? |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| resilient | 0.8373 | 0.8424 | 0.000 | 0 | 0 | 0 | 1.386 | Không |
| cached | 0.9124 | 0.9645 | 0.592 | 192 | 0 | 2 | 0.955 | Có |

| Tham số | Giá trị | Lý do |
|---|---:|---|
| similarity_threshold | 0.95 | Ngưỡng 0.80 từng trộn câu gần nghĩa và tạo 181 `other_question`; 0.95 đạt 0 wrong answer. |
| ttl_s | 30 s | Giới hạn tài liệu shipping đổi không báo trước còn 2 outdated answer, dưới 15. |
| max_stale_s | 360 s | Bao phủ outage 120 s; phục vụ được 192 stale FAQ và FAQ availability 0.9645. |

Thí nghiệm cache (`reports/bonus.json`):

1. **Ngưỡng:** 0.80 cho hit ratio 0.587 nhưng trả sai 182 FAQ (`other_question`); 0.95 cho hit ratio 0.592 và 0 sai; 0.97 vẫn 0 sai nhưng hit ratio giảm còn 0.495 và chi phí/tốt tăng từ 0.955 lên 1.020. Vì vậy 0.95 là điểm cân bằng an toàn.
2. **TTL:** 30/60/300 s lần lượt cho outdated answer 2/3/95, hit ratio 0.592/0.652/0.731 và cost/turn 0.955/0.915/0.863. Webhook chỉ invalidates `policy/refund`; shipping đổi không báo trước nên TTL là giới hạn duy nhất cho dữ liệu cũ. TTL 30 giữ freshness tốt nhất mà vẫn vượt mục tiêu hit ratio.
3. **Stale-if-error:** đặt `max_stale_s=0` làm FAQ availability giảm từ 0.9645 xuống 0.8529, hit ratio từ 0.592 xuống 0.480 và stale served từ 192 xuống 0; 438 call GiveUp thay vì 246. Cửa sổ stale là lớp fallback khi toàn bộ provider sập.

Không cache câu hỏi cá nhân, kể cả theo user, vì các câu trả lời phụ thuộc trạng thái tài khoản/đơn hàng, có nguy cơ lộ dữ liệu và invalidation khó bảo đảm. Khi cache giữ dashboard xanh lúc provider sập, vẫn alert theo error/give-up rate của upstream và tỷ lệ stale served; ở đây có 94 lỗi `service_unavailable` dù FAQ vẫn phục vụ được.
