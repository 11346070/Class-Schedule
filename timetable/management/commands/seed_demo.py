"""建立課堂展示用資料。可重複執行，會把展示帳號恢復成同一套結果。"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from timetable.data_store import course_store
from timetable.models import (
    Classroom,
    Course,
    CourseMeeting,
    CourseReview,
    Enrollment,
    Favorite,
    ModuleCreditLimit,
    SchoolClass,
    Semester,
    StudentProfile,
    StudyRecord,
    Teacher,
    UserCreditLimit,
)

DEMO_PASSWORD = "ClassDemo2026"
CURRENT_CODE = "114-1"
CURRENT_NAME = "114學年度第1學期"

# 展示學生目前會選到的課。必修改由班級自動加入。
# 資訊模組選滿 6 學分，多的一門留在收藏，用來示範上限。
ELECTIVES = ("CS302", "CS304", "GE204", "ART102")
FAVORITES = ("FIN201", "INF210", "GE101", "TEST01")

ROOMS = {
    "CS101": "資訊館 101",
    "CS102": "資訊館 102",
    "CS103": "資訊館 201",
    "CS110": "資訊館 電腦教室",
    "CS201": "資訊館 301",
    "CS202": "資訊館 302",
    "CS203": "資訊館 303",
    "CS301": "資訊館 401",
    "CS302": "資訊館 402",
    "CS303": "資訊館 403",
    "CS304": "資訊館 404",
    "INF210": "資訊館 405",
    "GE101": "綜合大樓 101",
    "GE102": "綜合大樓 102",
    "GE103": "綜合大樓 103",
    "GE104": "綜合大樓 104",
    "GE201": "綜合大樓 201",
    "GE202": "綜合大樓 202",
    "GE203": "綜合大樓 203",
    "GE204": "綜合大樓 204",
    "PE101": "體育館",
    "PE102": "體育館",
    "ART101": "藝文中心 101",
    "ART102": "藝文中心 102",
    "TEST01": "研究大樓 301",
    "TEST02": "研究大樓 302",
    "FIN201": "商學館 201",
    "FIN202": "商學館 202",
    "CS199": "研究大樓 201",
}

# 歷年成績。已通過才計入畢業；已過但不認列與未通過要能在進度頁篩出來。
HISTORY = [
    ("112-1", "CHIN1", "國文(一)", 2, "通識", "", StudyRecord.STATUS_PASSED),
    ("112-1", "MATH0", "基礎數學", 3, "必修", "", StudyRecord.STATUS_PASSED),
    ("112-1", "CS001", "計算機概論", 3, "必修", "", StudyRecord.STATUS_PASSED),
    ("112-2", "CHIN2", "國文(二)", 2, "通識", "", StudyRecord.STATUS_PASSED),
    ("112-2", "MATH1", "線性代數", 3, "必修", "", StudyRecord.STATUS_PASSED),
    ("112-2", "ECO1", "經濟學(一)", 2, "通識", "", StudyRecord.STATUS_PASSED),
    ("113-1", "CALC1", "微積分(一)", 3, "必修", "", StudyRecord.STATUS_PASSED),
    ("113-1", "ENG1", "英文(一)", 2, "通識", "", StudyRecord.STATUS_PASSED),
    ("113-1", "PE0", "體育基礎", 1, "必修", "", StudyRecord.STATUS_PASSED),
    ("113-1", "CS090", "物件導向程式設計", 3, "選修", "資訊", StudyRecord.STATUS_PASSED),
    ("113-2", "CALC2", "微積分(二)", 3, "必修", "", StudyRecord.STATUS_PASSED),
    ("113-2", "ENG2", "英文(二)", 2, "通識", "", StudyRecord.STATUS_PASSED),
    ("113-2", "CS199", "專題先修", 2, "選修", "", StudyRecord.STATUS_PASSED),
    ("113-2", "FIN090", "會計學", 3, "選修", "金融", StudyRecord.STATUS_PASSED),
    ("113-2", "CS250", "網頁前端", 3, "選修", "資訊", StudyRecord.STATUS_UNRECOGNIZED),
    ("113-2", "PHY1", "普通物理", 3, "選修", "", StudyRecord.STATUS_FAILED),
]

REVIEWS = {
    "CS101": [("多", "適中"), ("多", "適中"), ("多", "難")],
    "CS301": [("多", "難"), ("多", "難"), ("適中", "適中")],
    "CS302": [("適中", "適中"), ("適中", "適中"), ("少", "易")],
    "CS303": [("多", "難"), ("多", "難")],
    "CS304": [("適中", "難"), ("適中", "難"), ("多", "難")],
    "INF210": [("多", "難"), ("多", "適中")],
    "GE204": [("少", "易"), ("少", "適中")],
    "ART102": [("適中", "易"), ("少", "易")],
}


def classroom(name):
    room, _created = Classroom.objects.get_or_create(name=name)
    return room


def teacher(name):
    person, _created = Teacher.objects.get_or_create(name=name)
    return person


def school_class(name):
    group, _created = SchoolClass.objects.get_or_create(name=name)
    return group


def write_fallback_pdf(path: Path, title: str):
    """沒有現成 PDF 時補一份可開啟的檔，讓大綱按鈕不會是空的。"""
    text = f"{title} course syllabus".encode("ascii", "replace")
    stream = b"BT /F1 18 Tf 72 760 Td (" + text + b") Tj ET"
    body = b"\n".join(
        [
            b"%PDF-1.4",
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
            b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj",
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj",
            b"4 0 obj<</Length " + str(len(stream)).encode("ascii") + b">>stream",
            stream,
            b"endstream endobj",
            b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj",
            b"trailer<</Size 6/Root 1 0 R>>",
            b"%%EOF",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


class Command(BaseCommand):
    help = "寫入課堂展示帳號、選課結果、評價與歷年成績。重複執行會還原展示帳號。"

    def handle(self, *args, **options):
        with transaction.atomic():
            course_store.ensure_seeded()
            current = self._semesters()
            self._courses(current)
            self._limits()
            users = self._users()
            self._clear_demo_activity(users)
            self._student(users["demo"])
            self._enroll(users)
            self._history(users["demo"])
            self._reviews(users)
            self._favorites(users["demo"])
            self._recount()
            Session.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("展示資料已寫入。"))
        self.stdout.write(f"學生帳號 demo / {DEMO_PASSWORD}")
        self.stdout.write(f"管理員 admin / {DEMO_PASSWORD}")

    def _semesters(self):
        current = Semester.objects.filter(is_current=True).first()
        if current is None:
            current = Semester(code=CURRENT_CODE, name=CURRENT_NAME, is_current=True)
            current.save()
        else:
            current.code = CURRENT_CODE
            current.name = CURRENT_NAME
            current.is_current = True
            current.save()
        Semester.objects.get_or_create(
            code="113-2",
            defaults={"name": "113學年度第2學期", "is_current": False},
        )
        course_store.get_graduation_requirement()
        return current

    def _courses(self, current):
        past = Semester.objects.get(code="113-2")
        info_class = school_class("資工一")
        Course.objects.update_or_create(
            course_id="CS110",
            defaults={
                "name": "程式設計實驗",
                "teacher": teacher("王教授"),
                "weekday": 1,
                "start_period": 3,
                "end_period": 4,
                "credits": 1,
                "course_type": "必修",
                "module": "",
                "school_class": info_class,
                "opens_to_all": False,
                "semester": current,
                "classroom": classroom(ROOMS["CS110"]),
                "total_quota": 60,
            },
        )
        Course.objects.update_or_create(
            course_id="INF210",
            defaults={
                "name": "資訊安全",
                "teacher": teacher("安教授"),
                "weekday": 3,
                "start_period": 9,
                "end_period": 11,
                "credits": 3,
                "course_type": "選修",
                "module": "資訊",
                "school_class": None,
                "opens_to_all": True,
                "semester": current,
                "classroom": classroom(ROOMS["INF210"]),
                "total_quota": 40,
            },
        )
        Course.objects.update_or_create(
            course_id="CS199",
            defaults={
                "name": "專題先修",
                "teacher": teacher("專教授"),
                "weekday": 4,
                "start_period": 6,
                "end_period": 7,
                "credits": 2,
                "course_type": "選修",
                "module": "",
                "school_class": info_class,
                "opens_to_all": False,
                "semester": past,
                "classroom": classroom(ROOMS["CS199"]),
                "total_quota": 30,
            },
        )
        for course_id, room_name in ROOMS.items():
            Course.objects.filter(pk=course_id).update(classroom=classroom(room_name))

        lab = Course.objects.get(pk="CS103")
        lab.extra_meetings.all().delete()
        CourseMeeting.objects.create(
            course=lab,
            weekday=1,
            start_period=11,
            end_period=12,
            classroom=classroom("資訊館 電腦教室"),
        )
        self._attach_syllabus("CS101", "程式設計(一) 課程大綱")
        self._attach_syllabus("CS302", "人工智慧 課程大綱")
        Course.objects.exclude(course_id__in=["CS101", "CS302"]).update(syllabus="")

    def _attach_syllabus(self, course_id, title):
        relative = f"syllabi/{course_id}.pdf"
        path = Path(settings.MEDIA_ROOT) / relative
        course = Course.objects.get(pk=course_id)
        old_name = course.syllabus.name if course.syllabus else ""
        if old_name and old_name != relative:
            course.syllabus.delete(save=False)
        if not path.exists() or path.stat().st_size < 50:
            write_fallback_pdf(path, title)
        course.syllabus.name = relative
        course.save(update_fields=["syllabus"])

    def _limits(self):
        ModuleCreditLimit.objects.update_or_create(
            module="資訊",
            defaults={"min_credits": 3, "max_credits": 6},
        )
        ModuleCreditLimit.objects.update_or_create(
            module="金融",
            defaults={"min_credits": 0, "max_credits": 9},
        )

    def _users(self):
        specs = [
            ("demo", "陳同學", False),
            ("admin", "系統管理員", True),
            ("seat01", "林同學", False),
            ("seat02", "黃同學", False),
            ("reviewer01", "評分生一", False),
            ("reviewer02", "評分生二", False),
            ("reviewer03", "評分生三", False),
        ]
        users = {}
        for username, name, is_admin in specs:
            user, _created = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com"},
            )
            user.email = f"{username}@example.com"
            user.first_name = name
            user.last_name = ""
            user.is_staff = is_admin
            user.is_superuser = is_admin
            if username in {"demo", "admin"}:
                user.set_password(DEMO_PASSWORD)
            else:
                user.set_unusable_password()
            user.save()
            users[username] = user
        return users

    def _clear_demo_activity(self, users):
        user_ids = [str(user.pk) for user in users.values()]
        Enrollment.objects.filter(user_id__in=user_ids).delete()
        Favorite.objects.filter(user_id__in=user_ids).delete()
        CourseReview.objects.filter(user_id__in=user_ids).delete()
        StudyRecord.objects.filter(user_id__in=user_ids).delete()
        self._recount()

    def _student(self, user):
        user_id = str(user.pk)
        profile, _created = StudentProfile.objects.get_or_create(user_id=user_id)
        profile.student_number = "11346001"
        profile.class_name = "資工一"
        profile.module = "資訊"
        profile.schedule_note = ""
        profile.notify_at_floor = True
        profile.notify_near_floor = True
        profile.notify_at_limit = True
        profile.save()
        UserCreditLimit.objects.update_or_create(
            user_id=user_id,
            defaults={"credit_limit": 25, "credit_floor": 20},
        )

    def _enroll(self, users):
        demo_id = str(users["demo"].pk)
        added = course_store.assign_required_courses(demo_id)
        if not added and not Enrollment.objects.filter(user_id=demo_id, course_id="CS101").exists():
            raise RuntimeError("必修沒有加入展示學生的課表。")
        for course_id in ELECTIVES:
            ok, message = course_store.enroll_course(demo_id, course_id)
            if not ok:
                raise RuntimeError(f"無法選入 {course_id}：{message}")
        for username in ("seat01", "seat02"):
            ok, message = course_store.enroll_course(str(users[username].pk), "TEST01")
            if not ok:
                raise RuntimeError(f"無法把 {username} 選入 TEST01：{message}")
        StudyRecord.objects.filter(
            user_id=demo_id,
            status=StudyRecord.STATUS_IN_PROGRESS,
        ).update(semester=CURRENT_CODE)

    def _history(self, user):
        user_id = str(user.pk)
        linked = {course.course_id: course for course in Course.objects.filter(course_id="CS199")}
        StudyRecord.objects.bulk_create(
            [
                StudyRecord(
                    user_id=user_id,
                    course=linked.get(code),
                    course_code=code,
                    course_name=name,
                    credits=credits,
                    course_type=course_type,
                    module=module,
                    semester=semester,
                    status=status,
                )
                for semester, code, name, credits, course_type, module, status in HISTORY
            ]
        )

    def _reviews(self, users):
        reviewers = [users["reviewer01"], users["reviewer02"], users["reviewer03"]]
        for course_id, opinions in REVIEWS.items():
            course = Course.objects.get(pk=course_id)
            for reviewer, (homework, exam) in zip(reviewers, opinions):
                CourseReview.objects.create(
                    user_id=str(reviewer.pk),
                    course=course,
                    homework=homework,
                    exam=exam,
                )
        ok, message = course_store.save_review(str(users["demo"].pk), "CS302", "適中", "適中")
        if not ok:
            raise RuntimeError(message)

    def _favorites(self, user):
        user_id = str(user.pk)
        for course_id in FAVORITES:
            ok, message = course_store.add_favorite(user_id, course_id)
            if not ok:
                raise RuntimeError(f"無法收藏 {course_id}：{message}")

    def _recount(self):
        for course in Course.objects.annotate(actual=Count("enrollments")):
            if course.enrolled_count != course.actual:
                course.enrolled_count = course.actual
                course.save(update_fields=["enrolled_count"])
