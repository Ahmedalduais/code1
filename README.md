<div align="center">

# Odoo 19 University ERP

### Integrated Higher Education Management System

<br/>

![Odoo 19](https://img.shields.io/badge/Odoo-19-875A7B?style=for-the-badge&logo=odoo&logoColor=white)
![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL 14+](https://img.shields.io/badge/PostgreSQL-14+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-LGPL--3.0-blue?style=for-the-badge)
![Version](https://img.shields.io/badge/Version-19.0.1.0.0-green?style=for-the-badge)
![Tests](https://img.shields.io/badge/Tests-805-brightgreen?style=for-the-badge)

<br/>

A comprehensive ERP system built on Odoo 19 for managing all academic, administrative, and financial operations of higher education institutions.

<br/>

</div>

---

## Why This System?

|  | Feature | Details |
|--|---------|---------|
| 🏗️ | **Advanced Architecture** | 21 interconnected modules with three-tier design |
| 🎓 | **Complete Academic Management** | From admission to graduation with full academic records |
| 👨‍🏫 | **Faculty Management** | Assignments, workloads, committees, contracts, publications |
| 📊 | **Flexible Grading** | Customizable grading engine with automatic GPA calculation |
| 💰 | **Smart Finance** | Fees, scholarships, payment plans, invoices |
| 🌐 | **Web Portals** | Dedicated portals for students and faculty with dashboards |
| 🌍 | **Full Arabic Support** | RTL interfaces with translation support (`translate=True`) |
| 📈 | **Professional Reports** | 8+ ready-made PDF reports with charts and analytics |
| ✅ | **Comprehensive Tests** | 805 test methods covering all modules |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Tier 1 — Mandatory                     │
├──────────────────────┬──────────────────────────────────┤
│   university_core    │   university_grading             │
│   Core Foundation    │   Grading Framework              │
└──────────┬───────────┴──────────┬───────────────────────┘
           │                      │
┌──────────▼──────────────────────▼───────────────────────┐
│                Tier 2 — Auto-Installed                  │
├──────────────┬──────────────┬─────────────┬─────────────┤
│  curriculum  │   faculty    │   student   │  timetable  │
│  Curriculum  │   Faculty    │   Students  │  Timetable  │
└──────┬───────┴──────┬───────┴──────┬──────┴─────────────┘
       │              │              │
┌──────▼──────────────▼──────────────▼─────────────────────┐
│                Tier 3 — Optional                         │
├────────────┬────────────┬────────────┬───────────────────┤
│ admission  │    exam    │ gradebook  │     finance       │
│ Admission  │   Exams    │ Gradebook  │     Finance       │
├────────────┼────────────┼────────────┼───────────────────┤
│   portal   │accreditation│ research  │     library       │
│   Portal   │Accreditation│ Research  │     Library       │
├────────────┼────────────┼────────────┼───────────────────┤
│  housing   │ transport  │  alumni    │      lms          │
│  Housing   │ Transport  │  Alumni    │      LMS          │
├────────────┼────────────┼────────────┼───────────────────┤
│  reports   │  project   │ internship │                   │
│  Reports   │  Project   │ Internship │                   │
└────────────┴────────────┴────────────┴───────────────────┘
```

---

## Modules

### Tier 1 — Foundation

<details>
<summary><strong>university_core</strong> — Core Foundation</summary>

<br/>

**Depends:** `base` · `mail` · `contacts`

The foundational module that all other modules depend on.

| Component | Description |
|-----------|-------------|
| University | Main university entity (inherits `res.partner`) |
| Branch | Geographic branches |
| College | Colleges and institutes |
| Department | Academic departments |
| Program | Academic programs with state workflow |
| Academic Year | Academic years and terms |
| Person Model | Base person entity for students/faculty |
| Mixins | ArchivableMixin, SequenceMixin, MultiCompanyMixin, PersonMixin |

**Models:** 13 · **Files:** 33 · **Tests:** 57

</details>

<details>
<summary><strong>university_grading</strong> — Grading Framework</summary>

<br/>

**Depends:** `university_core` · **Auto-install:** Yes

| Component | Description |
|-----------|-------------|
| Grade Letter | Flexible letter grades (A, A-, B+, etc.) |
| Grading System | Point-based, percentage, or letter systems |
| Grading Engine | AbstractModel engine for custom grading logic |
| Grading Calculator | Automatic GPA calculation |
| Grade Conversion | Convert between different grading systems |

**Models:** 5 · **Files:** 17 · **Tests:** 45

</details>

---

### Tier 2 — Core Operations

<details>
<summary><strong>university_curriculum</strong> — Curriculum Management</summary>

<br/>

**Depends:** `university_core` · **Auto-install:** Yes

- Courses, course types, and delivery methods
- Prerequisites and equivalencies
- Learning outcomes and syllabi
- Evaluation types and assessment items
- Program-course linking with credit hours

**Models:** 11 · **Files:** 23 · **Tests:** 48

</details>

<details>
<summary><strong>university_faculty</strong> — Faculty Management</summary>

<br/>

**Depends:** `university_core` · `hr` · **Auto-install:** Yes

- Academic ranks (Professor, Associate Professor, etc.)
- Faculty members (linked to `hr.employee`)
- Teaching assignments and workloads
- Publications and research
- Committees and members
- Employment contracts with full workflow

**Models:** 8 · **Files:** 22 · **Tests:** 67

</details>

<details>
<summary><strong>university_student</strong> — Student Records</summary>

<br/>

**Depends:** `university_core` · `university_curriculum` · **Auto-install:** Yes

- Student status management
- Academic enrollment with course lines
- Internal/external transfers
- Student documents with verification
- Attendance tracking (present/absent/late/excused)
- Academic advisor assignment

**Models:** 9 · **Files:** 22 · **Tests:** 96

</details>

<details>
<summary><strong>university_timetable</strong> — Timetable Management</summary>

<br/>

**Depends:** `university_curriculum` · `university_faculty` · **Auto-install:** Yes

- Classroom types and specifications
- Classrooms with capacity and facilities
- Time slots with conflict detection
- Weekly timetables per term
- Schedule lines with faculty/classroom/course/slot
- **Conflict prevention:** Faculty, classroom, and course-section conflicts

**Models:** 6 · **Files:** 20 · **Tests:** 54

</details>

---

### Tier 3 — Optional Modules

<details>
<summary><strong>university_admission</strong> — Admission & Registration</summary>

<br/>

**Depends:** `university_core` · `university_student`

Application → Review → Interview → Decision → Enrollment

- Admission criteria (GPA, age, test scores, fees)
- Document requirements with fulfillment tracking
- Application workflow with full lifecycle
- Interview scheduling and scoring
- Decision records with scholarship offers
- **Auto-creates student record on enrollment**

**Models:** 5 · **Files:** 18 · **Tests:** 45

</details>

<details>
<summary><strong>university_exam</strong> — Exam Management</summary>

<br/>

**Depends:** `university_curriculum` · `university_grading`

- Exam types (written, oral, practical, online, mixed)
- Exam scheduling and lifecycle management
- Exam rooms with equipment and capacity
- Invigilator assignments with roles
- Violation reporting with severity levels
- Special accommodations for disabilities

**Models:** 7 · **Files:** 21 · **Tests:** 50

</details>

<details>
<summary><strong>university_gradebook</strong> — Gradebook & Transcripts</summary>

<br/>

**Depends:** `university_student` · `university_curriculum` · `university_grading`

- Gradebook per course/term/section
- Student grade lines with entry tracking
- Individual grade entries with weights
- Final grades with GPA, rank, and pass/fail
- Approval workflow (submission → review → approval → publication)
- Official academic transcripts
- GPA calculation with cumulative support

**Models:** 7 · **Files:** 22 · **Tests:** 40

</details>

<details>
<summary><strong>university_finance</strong> — Financial Management</summary>

<br/>

**Depends:** `university_core` · `university_student` · `account`

- Fee types (tuition, lab, library, registration, etc.)
- Fee structures with installment plans
- Scholarships with types and amounts
- Student invoices (linked to `account.move`)
- Payment plans with automatic installments

**Models:** 10 · **Files:** 19 · **Tests:** 30

</details>

<details>
<summary><strong>university_portal</strong> — Student & Faculty Portals</summary>

<br/>

**Depends:** `website` · `university_student` · `university_faculty`

- Student portal with dashboard
- Faculty portal with dashboard
- Customizable dashboard widgets
- Notification system
- QWeb frontend templates

**Models:** 4 · **Files:** 21 · **Tests:** 20

</details>

<details>
<summary><strong>university_accreditation</strong> — Academic Accreditation</summary>

<br/>

**Depends:** `university_core` · `university_curriculum` · `university_faculty` · `university_gradebook`

- Accreditation bodies (national/regional/international)
- Standards with hierarchy and weights
- Program accreditation with periodic reviews
- Evidence-based reports
- Comprehensive self-study documents

**Models:** 5 · **Files:** 16 · **Tests:** 25

</details>

<details>
<summary><strong>university_research</strong> — Scientific Research</summary>

<br/>

**Depends:** `university_faculty`

- Academic journals with impact factor
- Conferences with paper submission
- Research grants and funding
- Ethics committee reviews
- Research projects with milestones
- Publications with citations and indexing

**Models:** 7 · **Files:** 20 · **Tests:** 35

</details>

<details>
<summary><strong>university_library</strong> — Library Management</summary>

<br/>

**Depends:** `university_core`

- Authors and hierarchical categories
- Books with ISBN, publisher, and e-book support
- Borrowing system (students, faculty, staff, externals)
- Digital repository (theses, papers, lectures)
- Fine calculations (late, damage, loss)

**Models:** 6 · **Files:** 19 · **Tests:** 30

</details>

<details>
<summary><strong>university_housing</strong> — Housing Management</summary>

<br/>

**Depends:** `university_core` · `university_student`

- Room types (double, single, suite)
- Buildings with facilities and occupancy stats
- Rooms with capacity, rent, and status
- Allocation workflow (draft → active → completed)
- Housing contracts (semester/yearly/monthly)
- Maintenance requests with priority and workflow

**Models:** 6 · **Files:** 18 · **Tests:** 30

</details>

<details>
<summary><strong>university_transport</strong> — Transport Management</summary>

<br/>

**Depends:** `university_core` · `university_student`

- Fleet vehicles with maintenance tracking
- Routes with stops and schedules
- Transport passes (semester/yearly/monthly)
- Daily attendance and ridership tracking

**Models:** 5 · **Files:** 16 · **Tests:** 25

</details>

<details>
<summary><strong>university_alumni</strong> — Alumni Management</summary>

<br/>

**Depends:** `university_student`

- Alumni member profiles
- Events with RSVP tracking
- Donations (cash/in-kind/recurring)
- Professional networking by industry/region
- Career tracking and job postings

**Models:** 5 · **Files:** 16 · **Tests:** 25

</details>

<details>
<summary><strong>university_lms</strong> — Learning Management System</summary>

<br/>

**Depends:** `university_curriculum` · `website`

- Online courses with modules and enrollment
- Content types (video, document, link, text)
- Assignments with submission and late penalties
- Quizzes with multiple question types
- Forums with pinned/locked threads
- Student progress tracking with completion %

**Models:** 15 · **Files:** 23 · **Tests:** 30

</details>

<details>
<summary><strong>university_reports</strong> — Advanced Reporting</summary>

<br/>

**Depends:** `university_core`

- Report templates with dynamic parameters
- Custom report builder with filters and columns
- Scheduled reports (daily/weekly/monthly/quarterly)
- Dashboard widgets (KPI/chart/table/calendar/gauge)
- 8+ ready-made PDF reports

**Models:** 5 · **Files:** 26 · **Tests:** 20

</details>

<details>
<summary><strong>university_project</strong> — Graduation Projects</summary>

<br/>

**Depends:** `university_curriculum` · `university_faculty` · `university_student` · `university_research`

- Project themes and categories
- Proposals with approval workflow
- Teams with per-member contribution tracking
- Faculty supervisors
- Milestones and timelines
- Defense sessions with committees
- Multi-criteria evaluation (individual/group/mixed)

**Models:** 16 · **Files:** 39 · **Tests:** 35

</details>

<details>
<summary><strong>university_internship</strong> — Field Training / Internship</summary>

<br/>

**Depends:** `university_core` · `university_student` · `university_faculty` · `university_curriculum` · `hr`

- External training entities (companies)
- Entity supervisors from industry
- Internship opportunities with skill requirements
- Application and interview process
- Teams with contribution tracking
- Daily logs with dual approval (academic + field supervisor)
- Attendance with check-in/out times
- Weekly and final reports
- Multi-type evaluations (individual/group/mixed)
- Completion records and certificates

**Models:** 21 · **Files:** 49 · **Tests:** 55

</details>

---

## Statistics

| Metric | Count |
|--------|-------|
| **Modules** | 21 |
| **Python Files** | 229 |
| **XML Files** | 230 |
| **CSV Files** | 21 |
| **Test Files** | 76 |
| **Test Methods** | 805 |
| **Models** | 120+ |
| **PDF Reports** | 8+ |
| **Total Files** | 557 |

---

## Workflows

| Module | State Transitions |
|--------|-------------------|
| **Admission** | draft → submitted → under_review → interview_scheduled → accepted → enrolled |
| **Exam** | draft → scheduled → ongoing → completed / cancelled |
| **Gradebook** | draft → active → locked → closed |
| **Project** | proposal → approval → execution → defense → evaluation → publication |
| **Internship** | opportunity → application → interview → team → execution → evaluation → certificate |
| **Housing** | draft → active → completed → cancelled |
| **Faculty** | active ↔ on_leave → terminated |
| **Student** | prospective → active → graduated / suspended / withdrawn |

---

## Installation

### Prerequisites

| Component | Minimum Version |
|-----------|----------------|
| Odoo | 19.0 Community/Enterprise |
| Python | 3.10+ |
| PostgreSQL | 14+ |

### Step 1 — Clone the Repository

```bash
cd /path/to/odoo/addons
git clone https://github.com/Ahmedalduais/university_models_odoo.git
```

### Step 2 — Configure Addons Path

```ini
# odoo.conf
[options]
addons_path = /path/to/odoo/addons,/path/to/university_models_odoo
```

### Step 3 — Install Modules

Navigate to **Settings → Apps** and search for **"University"** to install the desired modules.

> **Note:** The following modules are auto-installed when `university_core` is installed:
> `university_grading` · `university_curriculum` · `university_faculty` · `university_student` · `university_timetable`

---

## Running Tests

```bash
# Run all university module tests
odoo-bin -d your_database -i university_core --test-enable --stop-after-init

# Run tests for a specific module
odoo-bin -d your_database -i university_student --test-enable --stop-after-init
```

---

## Key Features

### Inheritance Patterns

| Pattern | Usage | Examples |
|---------|-------|----------|
| `_inherits` (Delegation) | Share partner/person data without duplicating | `uni.university` → `res.partner` |
| `_inherit` (Classic) | Extend existing models | `uni.grading.calculator` ← `uni.grading.engine` |
| `AbstractModel` | Reusable mixins | `uni.mixin.archivable`, `uni.mixin.sequence` |

### Constraint Types

| Type | Purpose | Example |
|------|---------|---------|
| SQL Constraints | Database-level uniqueness and checks | `unique(university_id, code)` |
| Python Constraints | Complex business logic validation | Date ranges, grade ranges, conflict detection |
| Computed Fields | Auto-calculated values | GPA, total credits, counts |

### Conflict Detection

The timetable module includes comprehensive conflict prevention:
- **Faculty conflicts** — Same faculty cannot teach two sessions at the same time
- **Classroom conflicts** — Same room cannot host two sessions at the same time
- **Course-section conflicts** — Same course+section cannot appear twice in the same slot

---

## Contributing

1. Fork this repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## License

This project is licensed under **LGPL-3.0**.

---

<div align="center">

**Built with ❤️ for Higher Education**

[Report Bug](https://github.com/Ahmedalduais/university_models_odoo/issues) · [Request Feature](https://github.com/Ahmedalduais/university_models_odoo/issues)

</div>
