<div align="center">

# 🎓 Odoo 19 University ERP

### نظام إدارة مؤسسات التعليم العالي المتكامل

<br/>

![Odoo 19](https://img.shields.io/badge/Odoo-19-875A7B?style=for-the-badge&logo=odoo&logoColor=white)
![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL 14+](https://img.shields.io/badge/PostgreSQL-14+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-LGPL--3.0-blue?style=for-the-badge)
![Version](https://img.shields.io/badge/Version-19.0.1.0.0-green?style=for-the-badge)

<br/>

**نظام متكامل مبني على Odoo 19 لإدارة جميع العمليات الأكاديمية والإدارية والمالية لمؤسسات التعليم العالي**

<br/>

</div>

---

## ✨ لماذا هذا النظام؟

<div dir="rtl">

|  | الميزة | التفاصيل |
|--|--------|----------|
| 🏗️ | **بنية معمارية متقدمة** | 21 وحدة مترابطة بتصميم ثلاثي الطبقات |
| 🎓 | **إدارة أكاديمية شاملة** | من القبول إلى التخرج مع سجل أكاديمي كامل |
| 👨‍🏫 | **هيئة تدريس متكاملة** | التكليفات، الأحمال، اللجان، العقود، الأبحاث |
| 📊 | **نظام تقييم مرن** | محرك تقييم قابل للتخصيص مع حساب GPA |
| 💰 | **إدارة مالية ذكية** | الرسوم، المنح، خطط الدفع، الفواتير |
| 🌐 | **بوابات إلكترونية** | واجهات مخصصة للطلاب وأعضاء هيئة التدريس |
| 📱 | **دعم كامل للعربية** | واجهات RTL مع دعم الترجمة |
| 📈 | **تقارير احترافية** | 8+ تقارير PDF جاهزة مع رسوم بيانية |

</div>

---

## 🏛️ الهيكل المعماري

<div dir="rtl">

```
┌─────────────────────────────────────────────────────────┐
│                  الطبقة الأولى (إلزامية)                │
├──────────────────────┬──────────────────────────────────┤
│   university_core    │   university_grading             │
│   الأساس المشترك    │   إطار التقييم                   │
└──────────┬───────────┴──────────┬───────────────────────┘
           │                      │
┌──────────▼──────────────────────▼───────────────────────┐
│                 الطبقة الثانية (افتراضية)               │
├──────────────┬──────────────┬─────────────┬─────────────┤
│  curriculum  │   faculty    │   student   │  timetable  │
│  المناهج     │  هيئة التدريس│   الطلاب    │  الجدول     │
└──────┬───────┴──────┬───────┴──────┬──────┴─────────────┘
       │              │              │
┌──────▼──────────────▼──────────────▼─────────────────────┐
│                   الطبقة الثالثة (اختيارية)              │
├────────────┬────────────┬────────────┬───────────────────┤
│ admission  │    exam    │ gradebook  │     finance       │
│ القبول     │  الامتحانات│ الدرجات    │    المالية        │
├────────────┼────────────┼────────────┼───────────────────┤
│   portal   │ accreditation│ research │     library       │
│ البوابات   │   الاعتماد  │ البحث    │    المكتبة        │
├────────────┼────────────┼────────────┼───────────────────┤
│  housing   │ transport  │  alumni    │      lms          │
│ الإقامة    │  النقل     │ الخريجون  │  إدارة التعلم     │
├────────────┼────────────┼────────────┼───────────────────┤
│  reports   │  project   │ internship │                   │
│ التقارير   │المشاريع    │ التدريب    │                   │
└────────────┴────────────┴────────────┴───────────────────┘
```

</div>

---

## 📦 الوحدات

<div dir="rtl">

### الطبقة الأولى — الأساس

</div>

<details>
<summary><strong>🔷 university_core</strong> — الأساس المشترك</summary>

<br/>

**الاعتماد:** `base` · `mail` · `contacts`

الوحدة الأساسية التي تقوم عليها جميع الوحدات الأخرى.

| المكون | الوصف |
|--------|-------|
| الجامعة | كيان الجامعة الرئيسي (inherits res.partner) |
| الفرع | الفروع الجغرافية |
| الكلية | الكليات والمعاهد |
| القسم | الأقسام الأكاديمية |
| البرنامج | البرامج الدراسية |
| السنة الدراسية | السنوات والفترات الأكاديمية |
| نموذج الشخص | كيان أساسي لتمثيل الأشخاص |
| Mixins | ArchivableMixin, SequenceMixin, MultiCompanyMixin |

**النماذج:** 13 · **الملفات:** 33

</details>

<details>
<summary><strong>🔷 university_grading</strong> — إطار التقييم</summary>

<br/>

**الاعتماد:** `university_core` · **التثبيت التلقائي:** نعم

| المكون | الوصف |
|--------|-------|
| الدرجات الحرفية | نظام درجات مرن (A, A-, B+, ...) |
| أنظمة التقييم | قائمة على النقاط / النسبة / الحروف |
| محرك التقييم | نموذج مجرد قابل للتخصيص |
| حاسبة المعدل | حساب GPA تلقائي |
| تحويل الدرجات | بين الأنظمة المختلفة |

**النماذج:** 5 · **الملفات:** 17

</details>

---

<div dir="rtl">

### الطبقة الثانية — العمليات الأساسية

</div>

<details>
<summary><strong>🔷 university_curriculum</strong> — المناهج والبرامج</summary>

<br/>

**الاعتماد:** `university_core` · **التثبيت التلقائي:** نعم

- إدارة المقررات والأنواع وأساليب التدريس
- المتطلبات السابقة والمعادلات
- نتائج المناهج والمخططات الدراسية
- أنواع التقييمات و线路 التقييم
- ربط البرامج بالمقررات

**النماذج:** 11 · **الملفات:** 23

</details>

<details>
<summary><strong>🔷 university_faculty</strong> — هيئة التدريس</summary>

<br/>

**الاعتماد:** `university_core` · `hr` · **التثبيت التلقائي:** نعم

- الرتب الأكاديمية (أستاذ مشارك، أستاذ مساعد، ...)
- أعضاء هيئة التدريس (مرتبط بـ hr.employee)
- التكليفات الأكاديمية والأحمال
- المنشورات والأبحاث
- اللجان وأعضاؤها
- العقود

**النماذج:** 8 · **الملفات:** 22

</details>

<details>
<summary><strong>🔷 university_student</strong> — سجلات الطلاب</summary>

<br/>

**الاعتماد:** `university_core` · `university_curriculum` · **التثبيت التلقائي:** نعم

- حالات الطالب وإدارتها
- التسجيل الأكاديمي
- النقل الجامعي
- وثائق الطالب
- الحضور والغياب
- الموجه الأكاديمي

**النماذج:** 9 · **الملفات:** 22

</details>

<details>
<summary><strong>🔷 university_timetable</strong> — الجدول الزمني</summary>

<br/>

**الاعتماد:** `university_curriculum` · `university_faculty` · **التثبيت التلقائي:** نعم

- أنواع القاعات والقاعات
- حجز القاعات (منع التعارض)
- الفترات الزمنية
- الجداول الدراسية لكل فصل

**النماذج:** 6 · **الملفات:** 20

</details>

---

<div dir="rtl">

### الطبقة الثالثة — الوحدات الاختيارية

</div>

<details>
<summary><strong>🔷 university_admission</strong> — القبول والتسجيل</summary>

<br/>

**الاعتماد:** `university_core` · `university_student`

طلب القبول → المراجعة → المقابلة → القرار → التسجيل

**النماذج:** 5 · **الملفات:** 18

</details>

<details>
<summary><strong>🔷 university_exam</strong> — إدارة الامتحانات</summary>

<br/>

**الاعتماد:** `university_curriculum` · `university_grading`

أنواع الامتحانات · الجداول · قاعات المراقبة · المخالفات · التسهيلات

**النماذج:** 7 · **الملفات:** 21

</details>

<details>
<summary><strong>🔷 university_gradebook</strong> — دفتر الدرجات</summary>

<br/>

**الاعتماد:** `university_student` · `university_curriculum` · `university_grading`

درجات المقررات · الدرجات النهائية · GPA · السجلات الرسمية · سير عمل الموافقة

**النماذج:** 7 · **الملفات:** 22

</details>

<details>
<summary><strong>🔷 university_finance</strong> — الإدارة المالية</summary>

<br/>

**الidad:** `university_core` · `university_student` · `account`

أنواع الرسوم · هيكل الرسوم · الأقساط · المنح · الفواتير (account.move) · خطط الدفع

**النماذج:** 10 · **الملفات:** 19

</details>

<details>
<summary><strong>🔷 university_portal</strong> — البوابات الإلكترونية</summary>

<br/>

**الidad:** `website` · `university_student` · `university_faculty`

بوابة الطالب · بوابة أعضاء هيئة التدريس · لوحات معلومات · الإشعارات · قوالب QWeb

**النماذج:** 4 · **الملفات:** 21

</details>

<details>
<summary><strong>🔷 university_accreditation</strong> — الاعتماد الأكاديمي</summary>

<br/>

**الidaad:** `university_core` · `university_curriculum` · `university_faculty` · `university_gradebook`

هيئات الاعتماد · المعايير والوزنات · اعتماد البرامج · التقارير الدورية · الدراسة الذاتية

**النماذج:** 5 · **الملفات:** 16

</details>

<details>
<summary><strong>🔷 university_research</strong> — البحث العلمي</summary>

<br/>

**الidaad:** `university_faculty`

المجلات · المؤتمرات · المنح · الأخلاقيات · المشاريع · المنشورات · التعاون

**النماذج:** 7 · **الملفات:** 20

</details>

<details>
<summary><strong>🔷 university_library</strong> — المكتبة</summary>

<br/>

**الidaad:** `university_core`

المؤلفون · الفئات · الكتب (ISBN) · الاستعارة · المستودع الرقمي · الغرامات

**النماذج:** 6 · **الملفات:** 19

</details>

<details>
<summary><strong>🔷 university_housing</strong> — الإقامة الجامعية</summary>

<br/>

**الidaad:** `university_core` · `university_student`

أنواع الغرف · المباني · الغرف · التخصيص · العقود · الصيانة

**النماذج:** 6 · **الملفات:** 18

</details>

<details>
<summary><strong>🔷 university_transport</strong> — النقل</summary>

<br/>

**الidaad:** `university_core` · `university_student`

المركبات · المسارات · المحطات · تصاريح النقل · الحضور

**النماذج:** 5 · **الملفات:** 16

</details>

<details>
<summary><strong>🔷 university_alumni</strong> — الخريجون</summary>

<br/>

**الidaad:** `university_student`

أعضاء الجمعية · الفعاليات · التبرعات · الشبكات المهنية · تتبع الوظائف

**النماذج:** 5 · **الملفات:** 16

</details>

<details>
<summary><strong>🔷 university_lms</strong> — نظام إدارة التعلم</summary>

<br/>

**الidaad:** `university_curriculum` · `website`

الدورات · المحتوى (فيديو/مستندات) · الواجبات · الاختبارات · المنتديات · التقدم

**النماذج:** 15 · **الملفات:** 23

</details>

<details>
<summary><strong>🔷 university_reports</strong> — التقارير المتقدمة</summary>

<br/>

**الidaad:** `university_core`

قوالب التقارير · أداة البناء · التقارير المجدولة · عناصر Dashboard · 8+ تقارير PDF

**النماذج:** 5 · **الملفات:** 26

</details>

<details>
<summary><strong>🔷 university_project</strong> — المشاريع التخرجية</summary>

<br/>

**الidaad:** `university_curriculum` · `university_faculty` · `university_student` · `university_research`

الأفكار · المقترحات · الفرق · المرشدون · الجداول · الدفاع · التقييم · النشر

**النماذج:** 16 · **الملفات:** 39

</details>

<details>
<summary><strong>🔷 university_internship</strong> — التدريب الميداني</summary>

<br/>

**الidaad:** `university_core` · `university_student` · `university_faculty` · `university_curriculum` · `hr`

الكيانات الخارجية · الفرص · التقديمات · الفرق · السجلات · التقييم · الشهادات

**النماذج:** 21 · **الملفات:** 49

</details>

---

## 📊 الإحصائيات

<div align="center">

| الوحدات | ملفات Python | ملفات XML | ملفات CSV | النماذج | تقارير PDF |
|:-------:|:------------:|:---------:|:---------:|:-------:|:----------:|
| **21** | **229** | **230** | **21** | **120+** | **8+** |

</div>

---

## 🔄 سير العمل

<div dir="rtl">

| الوحدة | الخطوات |
|--------|---------|
| **القبول** | مسودة → مقدم → قيد المراجعة → مقابلة → مقبول/مرفوض → مسجل |
| **الامتحان** | مسودة → مجدول → جارٍ → مكتمل / ملغي |
| **الدرجات** | مسودة → مراجعة → موافقة → نشر → مقفل |
| **المشروع** | اقتراح → موافقة → تنفيذ → دفاع → تقييم → نشر |
| **التدريب** | فرصة → تقديم → مقابلة → فريق → تنفيذ → تقييم → شهادة |
| **الإقامة** | مسودة → نشط → مكتمل → ملغي |

</div>

---

## 🚀 التثبيت

<div dir="rtl">

### المتطلبات

| المكون | الحد الأدنى |
|--------|------------|
| Odoo | 19.0 Community/Enterprise |
| Python | 3.10+ |
| PostgreSQL | 14+ |

### الخطوة 1 — استنساخ المستودع

```bash
cd /path/to/odoo/addons
git clone https://github.com/Ahmedalduais/university_models_odoo.git
```

### الخطوة 2 — إعداد المسار

```ini
# odoo.conf
[options]
addons_path = /path/to/odoo/addons,/path/to/university_models_odoo
```

### الخطوة 3 — التثبيت

أدخل إلى **الإعدادات → التطبيقات** وابحث عن **"University"** ثم قم بتثبيت الوحدات المطلوبة.

> **ملاحظة:** الوحدات التالية تثبت تلقائياً عند تثبيت `university_core`:
> `university_grading` · `university_curriculum` · `university_faculty` · `university_student` · `university_timetable`

</div>

---

## 🤝 المساهمة

<div dir="rtl">

1. Fork هذا المستودع
2. أنشئ فرعاً جديداً: `git checkout -b feature/my-feature`
3. قم بالتعديل والالتزام: `git commit -m 'Add some feature'`
4. ادفع التغييرات: `git push origin feature/my-feature`
5. افتح Pull Request

</div>

---

## 📄 الترخيص

<div dir="rtl">

هذا المشروع مرخص تحت **LGPL-3.0**

</div>

---

<div align="center">

**Built with ❤️ for Higher Education**

[Report Bug](https://github.com/Ahmedalduais/university_models_odoo/issues) · [Request Feature](https://github.com/Ahmedalduais/university_models_odoo/issues)

</div>
