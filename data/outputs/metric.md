# Nội dung từ metric.pdf

--- Trang 1 (Nguồn: manual) ---

### Nội dung văn bản:

Các chỉ số đánh giá cho nhiệm vụ tóm tắt của
chatbot
1. Các chỉ số tự động
1.1. Chỉ số trùng lặp từ vựng (Lexical Overlap)
1.2. Chỉ số tương đồng ngữ nghĩa (Semantic Similarity)
1.3. Chỉ số trung thực & chính xác về sự thật (Factuality)
2. Chỉ số không cần bản tham chiếu (Reference-free /
Unsupervised)
1. BARTScore
2. QAEval
3. UniEval
3. Đánh giá của con người (Human Evaluation)
Mạch lạc, Liên quan, Tính dễ đọc và lưu loát, Trung
thực, Tính hữu ích.

### Bảng:

|  |  |
| --- | --- |
| Các chỉ số đánh giá cho nhiệm vụ tóm tắt của chatbot 1. Các chỉ số tự động 1.1. Chỉ số trùng lặp từ vựng (Lexical Overlap) 1.2. Chỉ số tương đồng ngữ nghĩa (Semantic Similarity) 1.3. Chỉ số trung thực & chính xác về sự thật (Factuality) 2. Chỉ số không cần bản tham chiếu (Reference-free / Unsupervised) 1. BARTScore 2. QAEval 3. UniEval 3. Đánh giá của con người (Human Evaluation) Mạch lạc, Liên quan, Tính dễ đọc và lưu loát, Trung thực, Tính hữu ích. |  |

--- Trang 2 (Nguồn: manual) ---

### Nội dung văn bản:

1. Các chỉ số tự động
1.1. Chỉ số trùng lặp từ vựng (Lexical Overlap)
ROUGE (Recall-Oriented Understudy for Gisting Evaluation):
ROUGE-N: đo n-gram overlap (thường dùng ROUGE-1, ROUGE-2).
ROUGE-L: dựa trên chuỗi con chung dài nhất (Longest Common Subsequence).
✅
Ưu điểm: phổ biến, dễ hiểu.
❌
Hạn chế: không nhận ra cách diễn đạt lại cùng nghĩa.
1.2. Chỉ số tương đồng ngữ nghĩa (Semantic Similarity)
BERTScore:
Tính cosine similarity giữa embedding ngữ cảnh của token (BERT/transformer).
Đưa ra precision, recall, F-score.
MoverScore:
Đo "khoảng cách Earth Mover" giữa embedding của hai văn bản.
Nắm được sự dịch chuyển ý nghĩa toàn cục.
BLEURT:
Mô hình deep learning được fine-tune theo đánh giá con người.
Xuất ra điểm phản ánh mức “giống đánh giá con người”.

### Bảng:

|  |  |
| --- | --- |
| 1. Các chỉ số tự động 1.1. Chỉ số trùng lặp từ vựng (Lexical Overlap) ROUGE (Recall-Oriented Understudy for Gisting Evaluation): ROUGE-N: đo n-gram overlap (thường dùng ROUGE-1, ROUGE-2). ROUGE-L: dựa trên chuỗi con chung dài nhất (Longest Common Subsequence). ✅ Ưu điểm: phổ biến, dễ hiểu. ❌ Hạn chế: không nhận ra cách diễn đạt lại cùng nghĩa. 1.2. Chỉ số tương đồng ngữ nghĩa (Semantic Similarity) BERTScore: Tính cosine similarity giữa embedding ngữ cảnh của token (BERT/transformer). Đưa ra precision, recall, F-score. MoverScore: Đo "khoảng cách Earth Mover" giữa embedding của hai văn bản. Nắm được sự dịch chuyển ý nghĩa toàn cục. BLEURT: Mô hình deep learning được fine-tune theo đánh giá con người. Xuất ra điểm phản ánh mức “giống đánh giá con người”. |  |

--- Trang 3 (Nguồn: manual) ---

### Nội dung văn bản:

1. Các chỉ số tự động
1.3. Chỉ số trung thực & chính xác về sự thật (Factuality)
Đảm bảo tóm tắt không bịa đặt thông tin.
QAGS (Question Answering and Generation for Summarization):
→
Sinh câu hỏi từ tóm tắt kiểm tra văn bản nguồn có trả lời được không.
→
Nếu không trả lời được tóm tắt có thể sai.
FactCC:
Mô hình phân loại (classification) để phát hiện inconsistency giữa nguồn và tóm tắt.
SummaC:
Dùng mô hình suy diễn (NLI – Natural Language Inference) để chấm điểm khả năng suy ra tóm tắt từ
nguồn.

### Bảng:

|  |  |
| --- | --- |
| 1. Các chỉ số tự động 1.3. Chỉ số trung thực & chính xác về sự thật (Factuality) Đảm bảo tóm tắt không bịa đặt thông tin. QAGS (Question Answering and Generation for Summarization): → Sinh câu hỏi từ tóm tắt kiểm tra văn bản nguồn có trả lời được không. → Nếu không trả lời được tóm tắt có thể sai. FactCC: Mô hình phân loại (classification) để phát hiện inconsistency giữa nguồn và tóm tắt. SummaC: Dùng mô hình suy diễn (NLI – Natural Language Inference) để chấm điểm khả năng suy ra tóm tắt từ nguồn. |  |

--- Trang 4 (Nguồn: manual) ---

### Nội dung văn bản:

2. Chỉ số không cần bản tham chiếu (Reference-free / Unsupervised)
1. BARTScore
Cách hoạt động:
Dùng mô hình sinh BART đã pretrained.
Tính log-likelihood (xác suất sinh ra text) để chấm điểm.
Có 2 hướng:
→
source summary: đo xem bản tóm tắt có hợp lý khi sinh từ văn bản nguồn không.
→
summary source: đo xem văn bản nguồn có khớp ngược lại với tóm tắt không.
→
Ý nghĩa: Điểm số càng cao tóm tắt càng “phù hợp” với nguồn theo xác suất mô hình.
Ưu điểm: Không cần bản tham chiếu.
Hạn chế: Phụ thuộc vào chất lượng mô hình nền (BART).
2. QAEval
Cách hoạt động:
Dựa trên ý tưởng của QAGS (Question Answering & Generation for Summarization).
Sinh ra các câu hỏi từ bản tóm tắt.
→ →
Dùng văn bản nguồn để trả lời nếu trả lời được nghĩa là tóm tắt trung thực.
Điểm khác với QAGS:
Có thể chạy không cần reference summary.
Chỉ cần nguồn gốc (source text) là đủ.
→
Ý nghĩa: Nếu tóm tắt chứa thông tin không có trong nguồn hệ thống QA sẽ không trả lời được.
Ưu điểm: Kiểm tra factuality trực tiếp.
Hạn chế: Tốn tài nguyên (vì cần QA model).

--- Trang 5 (Nguồn: manual) ---

### Nội dung văn bản:

2. Chỉ số không cần bản tham chiếu (Reference-free /
Unsupervised)
3. UniEval
Cách hoạt động:
Là một mô hình pretrained đa nhiệm cho nhiều loại evaluation.
Được huấn luyện để chấm điểm các tiêu chí như:
Relevance (liên quan)
Consistency (nhất quán, trung thực với nguồn)
Readability (dễ đọc, trôi chảy)
Không cần gold summary.
Ý nghĩa: Cho điểm “giống người” hơn, vì được fine-tune cho nhiều chiều chất lượng.
Ưu điểm: Bao phủ nhiều tiêu chí trong một mô hình.
Hạn chế: Cần mô hình pretrained riêng, không phổ biến bằng ROUGE/BERTScore.

### Bảng:

|  | -free / |
| --- | --- |
| 2. Chỉ số không cần bản tham chiếu (Reference-free / Unsupervised) 3. UniEval Cách hoạt động: Là một mô hình pretrained đa nhiệm cho nhiều loại evaluation. Được huấn luyện để chấm điểm các tiêu chí như: Relevance (liên quan) Consistency (nhất quán, trung thực với nguồn) Readability (dễ đọc, trôi chảy) Không cần gold summary. Ý nghĩa: Cho điểm “giống người” hơn, vì được fine-tune cho nhiều chiều chất lượng. Ưu điểm: Bao phủ nhiều tiêu chí trong một mô hình. Hạn chế: Cần mô hình pretrained riêng, không phổ biến bằng ROUGE/BERTScore. | -free / |

--- Trang 6 (Nguồn: manual) ---

### Nội dung văn bản:

3. Đánh giá của con người (Human Evaluation)
.
Mạch lạc (Coherence): Cấu trúc logic, ý nối tiếp mạch lạc.
Liên quan (Relevance): Bao phủ đủ ý chính, không bỏ sót chi tiết quan trọng.
Dễ đọc & lưu loát (Fluency): Ngữ pháp chuẩn, tự nhiên.
Trung thực (Faithfulness): Không thêm/bịa thông tin sai.
Hữu ích (Usefulness): Có giá trị thực cho người dùng.

### Bảng:

|  |  |
| --- | --- |
| 3. Đánh giá của con người (Human Evaluation) . Mạch lạc (Coherence): Cấu trúc logic, ý nối tiếp mạch lạc. Liên quan (Relevance): Bao phủ đủ ý chính, không bỏ sót chi tiết quan trọng. Dễ đọc & lưu loát (Fluency): Ngữ pháp chuẩn, tự nhiên. Trung thực (Faithfulness): Không thêm/bịa thông tin sai. Hữu ích (Usefulness): Có giá trị thực cho người dùng. |  |

--- Trang 7 (Nguồn: manual) ---

### Nội dung văn bản:

Nhóm Phương pháp Cách đo Ưu điểm Hạn chế Use case
So trùng n-gram, LCS Không nhận ra So sánh mô hình khi
Lexical Overlap ROUGE Dễ tính, phổ biến
(chuỗi con dài nhất) paraphrase có gold summary
Không tốt cho tóm tắt Ban đầu dùng cho
BLEU Precision của n-gram Phạt nội dung thừa
ngắn dịch, ít dùng tóm tắt
Trùng từ + stemming Gần human hơn Dịch & tóm tắt có
METEOR Vẫn dựa nhiều vào từ
+ đồng nghĩa BLEU paraphrase
Cosine sim. giữa Cần mô hình
Semantic Similarity BERTScore Hiểu paraphrase Đo ý nghĩa gần đúng
embedding từ (BERT) pretrained
Earth Mover Distance Nhận ra dịch chuyển So sánh tóm tắt dài,
MoverScore Tính toán nặng
giữa embedding ngữ nghĩa lớn nhiều paraphrase
Mô hình fine-tune
Tương quan cao với Cần mô hình đã huấn Đánh giá gần giống
BLEURT theo đánh giá con
human luyện human judgment
người
Pretrained evaluator
Đa tiêu chí, không Phụ thuộc model có Đánh giá chatbot sinh
UniEval đa nhiệm (fluency,
cần reference sẵn tóm tắt tự do
relevance,

### Bảng:

| Nhóm | Phương pháp | Cách đo | Ưu điểm | Hạn chế | Use case |
| --- | --- | --- | --- | --- | --- |
| Lexical Overlap | ROUGE | So trùng n-gram, LCS (chuỗi con dài nhất) | Dễ tính, phổ biến | Không nhận ra paraphrase | So sánh mô hình khi có gold summary |
|  | BLEU | Precision của n-gram | Phạt nội dung thừa | Không tốt cho tóm tắt ngắn | Ban đầu dùng cho dịch, ít dùng tóm tắt |
|  | METEOR | Trùng từ + stemming + đồng nghĩa | Gần human hơn BLEU | Vẫn dựa nhiều vào từ | Dịch & tóm tắt có paraphrase |
| Semantic Similarity | BERTScore | Cosine sim. giữa embedding từ (BERT) | Hiểu paraphrase | Cần mô hình pretrained | Đo ý nghĩa gần đúng |
|  | MoverScore | Earth Mover Distance giữa embedding | Nhận ra dịch chuyển ngữ nghĩa lớn | Tính toán nặng | So sánh tóm tắt dài, nhiều paraphrase |
|  | BLEURT | Mô hình fine-tune theo đánh giá con người | Tương quan cao với human | Cần mô hình đã huấn luyện | Đánh giá gần giống human judgment |
|  | UniEval | Pretrained evaluator đa nhiệm (fluency, relevance, | Đa tiêu chí, không cần reference | Phụ thuộc model có sẵn | Đánh giá chatbot sinh tóm tắt tự do |

--- Trang 8 (Nguồn: manual) ---

### Nội dung văn bản:

Nhóm Phương pháp Cách đo Ưu điểm Hạn chế Use case
Classifier check Không phát hiện mọi Tóm tắt tin tức, pháp
Factuality FactCC Nhanh, tự động
inconsistency sai fact lý
Sinh câu hỏi từ Kiểm tra fact chính Sinh QA tốn tài Đảm bảo không
QAGS
→
summary check xác nguyên “hallucination”
source
QA-based nhưng cải Không cần gold Khi không có bản
QuestEval Phức tạp hơn ROUGE
tiến hơn QAGS summary tham chiếu
NLI-based: check
SummaC Nhận diện mâu thuẫn Phụ thuộc NLI model Phát hiện lỗi logic, fact
entailment giữa
source summary
Đánh giá từng câu
DAE Chi tiết, theo câu Cần alignment Tóm tắt tài liệu dài
trong summary có
supported không
Tương tự QAGS nhưng Fact-check tài liệu
FEQA Tốt hơn cho câu dài Khó với câu phức tạp
tối ưu hóa QA khoa học
Dùng MultiNLI để Phát hiện mâu thuẫn
MNLI-doc Khó tính toàn văn bản Văn bản dài, đa chiều
check entailment đa câu
document level
Xác suất sinh
Không cần gold Dựa vào 1 model duy Khi chỉ có văn bản
→
Reference-free BARTScore (source summary,
summary nhất nguồn
ngược lại)
Sinh QA từ summary, Fact-check khi không
QAEval Đảm bảo fact Tốn chi phí QA
check bằng source có reference
Pretrained evaluator
Đa tiêu chí, không cần Phụ thuộc model có Đánh giá chatbot sinh
UniEval
đa nhiệm (fluency,
reference sẵn tóm tắt tự do
relevance,

### Bảng:

| Nhóm | Phương pháp | Cách đo | Ưu điểm | Hạn chế | Use case |
| --- | --- | --- | --- | --- | --- |
| Factuality | FactCC | Classifier check inconsistency | Nhanh, tự động | Không phát hiện mọi sai fact | Tóm tắt tin tức, pháp lý |
|  | QAGS | Sinh câu hỏi từ → summary check | Kiểm tra fact chính xác | Sinh QA tốn tài nguyên | Đảm bảo không “hallucination” |
|  | QuestEval | source QA-based nhưng cải tiến hơn QAGS | Không cần gold summary | Phức tạp hơn ROUGE | Khi không có bản tham chiếu |
|  | SummaC | NLI-based: check entailment giữa | Nhận diện mâu thuẫn | Phụ thuộc NLI model | Phát hiện lỗi logic, fact |
|  | DAE | source summary Đánh giá từng câu trong summary có | Chi tiết, theo câu | Cần alignment | Tóm tắt tài liệu dài |
|  | FEQA | supported không Tương tự QAGS nhưng tối ưu hóa QA | Tốt hơn cho câu dài | Khó với câu phức tạp | Fact-check tài liệu khoa học |
|  | MNLI-doc | Dùng MultiNLI để check entailment | Phát hiện mâu thuẫn đa câu | Khó tính toàn văn bản | Văn bản dài, đa chiều |
| Reference-free | BARTScore | document level Xác suất sinh → (source summary, ngược lại) | Không cần gold summary | Dựa vào 1 model duy nhất | Khi chỉ có văn bản nguồn |
|  | QAEval | Sinh QA từ summary, check bằng source | Đảm bảo fact | Tốn chi phí QA | Fact-check khi không có reference |
|  | UniEval | Pretrained evaluator đa nhiệm (fluency, relevance, | Đa tiêu chí, không cần reference | Phụ thuộc model có sẵn | Đánh giá chatbot sinh tóm tắt tự do |

--- Trang 9 (Nguồn: manual) ---

### Bảng:

|  |  |
| --- | --- |
| nghiên cứu tiêu biểu |  |

--- Trang 10 (Nguồn: manual) ---

### Nội dung văn bản:

nghiên cứu tiêu biểu
Human-like Summarization Evaluation with ChatGPT
Bài báo này cho thấy ChatGPT có khả năng thực hiện
đánh giá tóm tắt văn bản một cách linh hoạt theo
nhiều phương pháp giống con người, và trong nhiều
trường hợp, hiệu suất của nó vượt trội hơn các thước đo
tự động phổ biến

### Bảng:

|  |  |
| --- | --- |
| nghiên cứu tiêu biểu Human-like Summarization Evaluation with ChatGPT Bài báo này cho thấy ChatGPT có khả năng thực hiện đánh giá tóm tắt văn bản một cách linh hoạt theo nhiều phương pháp giống con người, và trong nhiều trường hợp, hiệu suất của nó vượt trội hơn các thước đo tự động phổ biến |  |

--- Trang 11 (Nguồn: manual) ---

### Nội dung văn bản:

nghiên cứu tiêu biểu
ChatGPT as a Factual Inconsistency Evaluator for Text
Summarization
Bài báo này tập trung chuyên sâu vào khả năng của
ChatGPT trong việc phát hiện sự mâu thuẫn về mặt
thông tin (factual inconsistency) và kết luận rằng nó có
tiềm năng lớn nhưng cũng bộc lộ những điểm yếu cần
khắc phục

### Bảng:

|  |  |
| --- | --- |
| nghiên cứu tiêu biểu ChatGPT as a Factual Inconsistency Evaluator for Text Summarization Bài báo này tập trung chuyên sâu vào khả năng của ChatGPT trong việc phát hiện sự mâu thuẫn về mặt thông tin (factual inconsistency) và kết luận rằng nó có tiềm năng lớn nhưng cũng bộc lộ những điểm yếu cần khắc phục |  |

--- Trang 12 (Nguồn: manual) ---

### Bảng:

|  |  |
| --- | --- |
| nghiên cứu tiêu biểu ChatGPT as a Factual Inconsistency Evaluator for Text Summarization |  |

