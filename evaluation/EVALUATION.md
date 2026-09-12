# Evaluation Report

كل الأرقام هنا حقيقية (من ملفات csv فعلية مُسلّمة من Person 1/3، أو من
سكريبتات تقييم اتشغلت فعليًا في `evaluation/`) — مفيش رقم واحد اتخترع.

---

## 1. Traditional ML Evaluation (بند 16) — Person 1

المصدر: `results/metrics.csv`

| Model               | Accuracy | Precision | Recall |    F1 | ROC-AUC |
|---------------------|---------:|----------:|-------:|------:|--------:|
| Logistic Regression |    53.8% |     50.9% |  53.8% | 52.3% |   56.4% |
| Random Forest       |    54.7% |     52.0% |  49.1% | 50.5% |   55.1% |
| **SVM**              |    **56.0%** |     53.1% |  56.6% | 54.8% |   57.1% |

**أفضل موديل:** SVM (أعلى Accuracy وF1 وROC-AUC، وإن كان الفرق عن الاتنين
التانيين صغير).

**تحليل صريح (مش تجميل للأرقام):** الأرقام الثلاثة قريبة جدًا من
الـ**50% (عشوائي تمامًا لمشكلة binary classification)**. الأسباب المرجحة:
1. الـDataset (`data/cleaned_prs.csv`) شكله **مولّد اصطناعيًا** (عناوين
   متكررة زي "Fix issue #N in module M" وأوصاف مكررة حرفيًا) مش
   PRs حقيقية مجروفة من GitHub فعليًا — يعني الإشارة الحقيقية اللي
   بتحدد "هل الـPR اتعمله merge ولا لأ" في الواقع مش بالضرورة موجودة
   في الـfeatures دي بنفس القوة اللي بتكون في بيانات حقيقية.
2. الـFeatures المتاحة (pr_size, code_churn, num_reviewers...) لوحدها
   مؤشرات ضعيفة نسبيًا على قرار الـmerge من غير سياق إضافي (محتوى الكود
   نفسه، جودة الاختبارات، سياسات الفريق...).

**False Positives / False Negatives:** الـmetrics.csv الحالي مفيهوش
confusion matrix مباشرة، لكن Recall ≈ Precision في الثلاث موديلات
(~50-56%) يعني الموديلات مش منحازة بشكل واضح لفئة معينة — الأخطاء
موزعة تقريبًا بالتساوي بين False Positives وFalse Negatives، مش أنها
"بتقول Approve لكل حاجة" أو العكس.

---

## 2. ML vs LLM Merge Prediction (بند 17)

المصدر: `evaluation/merge_prediction_comparison.py` (شغّال فعليًا على
20 عينة من نفس test set الحقيقي بتاع Person 1 — `data/test.csv`،
مع `target_merged` الحقيقي).

| Model                | Accuracy (n=20) |
|----------------------|----------------:|
| ML (SVM/RF, نفس الـfeatures الحقيقية) | 55.0% |
| LLM (MOCK_MODE)      |           55.0% |

**⚠️ تنويه مهم:** رقم الـLLM هنا **من MOCK_MODE** (مفيش
`ANTHROPIC_API_KEY`) — يعني ردوده template-based مش استنتاج فعلي، والرقم
ده بيثبت إن أداة المقارنة (harness) شغالة صح على نفس الـdataset ونفس
الـmetric، مش إنه تقييم حقيقي لجودة الـLLM. **لازم يتعاد تشغيله بـkey
حقيقي** قبل ما يتحط في التقرير النهائي كـ"مقارنة جودة".

---

## 3. LLM Code Review Evaluation (بند 18) — Person 3

المصدر: `results/review_metrics.csv` (n=8 لكل experiment/pattern).

هنا أرقام تجربة الـcontext D (Diff + Description + Commit + Repository
Context) كمثال:

| Pattern     | Accuracy | Precision | Recall |    F1 | BLEU  | ROUGE-L | Inference Time |
|-------------|---------:|----------:|-------:|------:|------:|--------:|---------------:|
| Zero-shot   |     100% |      100% |   100% |  100% | 0.115 |   0.103 |          0.05s |
| Few-shot    |    62.5% |     71.4% |  83.3% | 76.9% | 0.062 |   0.069 |          0.05s |
| Role-based  |    75.0% |     75.0% |   100% | 85.7% | 0.056 |   0.063 |          0.05s |
| Reflection  |    62.5% |     71.4% |  83.3% | 76.9% | 0.065 |   0.071 |          0.05s |

**⚠️ حجم العينة صغير جدًا (n=8)** — فرق نتيجة واحدة = 12.5 نقطة مئوية.
هذه الأرقام مؤشر أولي، مش دليل إحصائي قوي. لازم عينة أكبر لأي ادعاء نهائي.

---

## 4. Context Experiment (بند 19)

المصدر: `results/prompt_comparison.csv` (كل الـ4 contexts × 4 patterns).

متوسط الـAccuracy لكل context (عبر الـ4 patterns):

| Context                                          | متوسط Accuracy |
|---------------------------------------------------|---------------:|
| A) Diff only                                       |          50.0% |
| B) Diff + PR Description                           |          62.5% |
| C) Diff + PR Description + Commit Message          |          65.6% |
| **D) Diff + PR Description + Repository Context**  |          **75.0%** |

**الخلاصة:** كل context إضافي بيحسّن الأداء تدريجيًا، وContext D (أشمل
context) طلع الأفضل — منطقي، ومتوافق مع فرضية إن الـRepository Context
(اللي Person 5 بيوفرها) بتضيف قيمة حقيقية للمراجعة.

---

## 5. Prompt Experiment (بند 20)

متوسط الـAccuracy لكل prompt pattern (عبر الـ4 contexts):

| Pattern     | متوسط Accuracy |
|-------------|---------------:|
| Zero-shot   |          77.1% |
| Few-shot    |          56.3% |
| Role-based  |          62.5% |
| Reflection  |          56.3% |

**ملاحظة مثيرة للاهتمام:** Zero-shot طلع الأفضل في المتوسط، وده عكس
التوقع الشائع إن few-shot/role-based لازم يبقوا أحسن. ده يستاهل نقاش
في العرض (يمكن الـexamples المستخدمة في few-shot مش ممثلة كويس، أو
الـtask نفسها بسيطة بما يكفي إن zero-shot يكفيها). **مرة تانية: n=8،
فده ملاحظة أولية مش نتيجة نهائية.**

---

## 6. Supervisor Routing Accuracy (بند 21)

المصدر: `evaluation/supervisor_routing_eval.py` (شغّال فعليًا، 6 حالات).

**النتيجة: 5/6 = 83.3%** (heuristic fallback — مفيش `ANTHROPIC_API_KEY`).

**الحالة اللي فشلت:** PR فيه SQL query (`"SELECT * FROM users..."`) —
الهيوريستيك حط `context` زيادة عن اللازم لأن كلمة `"from "` (من الـSQL
`FROM` clause) اتفهمت غلط كإنها `import ... from ...`. ده مثال حي وواضح
ليه الـLLM-based supervisor (Phase B) المفروض يكون أدق من الهيوريستيك —
LLM هيفهم إن ده SQL query مش import statement.

نفس الـharness (`evaluation/supervisor_routing_eval.py`) شغال بالظبط على
`decide_llm`/`decide` لو `ANTHROPIC_API_KEY` اتوفر — بس غيّري
`DECISION_FN` في أول الملف.

---

## الخلاصة العامة

| المكوّن | جاهز للعرض | أهم تحفظ |
|---|---|---|
| Traditional ML | ✅ | Accuracy متواضعة (~50-56%)، على الأرجح بسبب طبيعة الـdataset الاصطناعي |
| LLM Merge Prediction | ⚠️ | لازم يتعاد التقييم بـAPI key حقيقي |
| LLM Code Review | ✅ | أرقام حقيقية، لكن n=8 صغيرة جدًا للثقة الإحصائية |
| Context/Prompt Experiments | ✅ | نتائج منطقية (Context D + Zero-shot أفضل)، بس نفس تحفظ حجم العينة |
| Supervisor Routing | ✅ | 83.3% بالهيوريستيك، مع مثال واضح ليه LLM-based أفضل |
