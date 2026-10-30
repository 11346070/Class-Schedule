import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from timetable.data_store import course_store
from timetable.models import StudentProfile


class ModuleCreditLimitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="module-student", password="password-1a")
        course_store.ensure_seeded()
        self.user_id = str(self.user.pk)

    def test_default_limits_do_not_block_or_remove_courses(self):
        enrolled, _message = course_store.enroll_course(self.user_id, "CS301")
        self.assertTrue(enrolled)
        self.assertEqual(course_store.get_module_limit_notes(self.user_id), [])

        from timetable.models import ModuleCreditLimit

        ModuleCreditLimit.objects.update_or_create(
            module="資訊", defaults={"min_credits": 0, "max_credits": 2}
        )
        self.assertTrue(course_store.is_user_enrolled(self.user_id, "CS301"))
        notes = course_store.get_module_limit_notes(self.user_id)
        self.assertEqual(len(notes), 1)
        self.assertIn("不會自動退選", notes[0])

        allowed, message = course_store.enroll_course(self.user_id, "CS302")
        self.assertFalse(allowed)
        self.assertIn("資訊模組學分上限", message)

    def test_module_minimum_blocks_drop_but_admin_force_still_works(self):
        from timetable.models import ModuleCreditLimit, UserCreditLimit

        UserCreditLimit.objects.update_or_create(
            user_id=self.user_id,
            defaults={"credit_floor": 0, "credit_limit": 25},
        )
        course_store.enroll_course(self.user_id, "FIN201")
        ModuleCreditLimit.objects.update_or_create(
            module="金融", defaults={"min_credits": 3, "max_credits": 0}
        )
        dropped, message = course_store.drop_course(self.user_id, "FIN201")
        self.assertFalse(dropped)
        self.assertIn("金融模組學分下限", message)
        self.assertTrue(course_store.is_user_enrolled(self.user_id, "FIN201"))

        forced, _message = course_store.drop_course(self.user_id, "FIN201", force=True)
        self.assertTrue(forced)
        self.assertFalse(course_store.is_user_enrolled(self.user_id, "FIN201"))

    def test_progress_page_shows_the_admin_module_limits(self):
        from timetable.models import ModuleCreditLimit

        ModuleCreditLimit.objects.update_or_create(
            module="資訊", defaults={"min_credits": 6, "max_credits": 12}
        )
        ModuleCreditLimit.objects.update_or_create(
            module="金融", defaults={"min_credits": 3, "max_credits": 0}
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("progress"))
        self.assertContains(response, "資訊模組學分下限 6，上限 12")
        self.assertContains(response, "金融模組學分下限 3，上限 不限制")


class RegisterPageTests(TestCase):
    def test_register_uses_the_same_card_as_login(self):
        response = self.client.get(reverse("register"))
        self.assertContains(response, "auth-solo-card")
        self.assertContains(response, "個人課表維護系統")
        self.assertContains(response, "至少 8 個字元")
        self.assertContains(response, "去登入")
        self.assertNotContains(response, "auth-aside")


class CourseDetailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="detail-student", password="password-1a")
        course_store.ensure_seeded()
        self.client.force_login(self.user)

    def test_enrolled_course_hides_the_status_banner_and_shows_module(self):
        enrolled, _message = course_store.enroll_course(str(self.user.pk), "CS301")
        self.assertTrue(enrolled)
        response = self.client.get(reverse("course_detail", args=["CS301"]))
        self.assertContains(response, "所屬模組")
        self.assertContains(response, "資訊")
        self.assertContains(response, "退選此課程")
        self.assertContains(response, "尚未上傳")
        self.assertNotContains(response, "您已選修此課程")
        self.assertNotContains(response, "檢視 PDF")

    def test_syllabus_can_be_viewed_and_downloaded(self):
        from django.core.files.base import ContentFile

        from timetable.models import Course

        course = Course.objects.get(pk="ART101")
        course.syllabus.save("ART101.pdf", ContentFile(b"%PDF-1.4 syllabus"), save=True)
        page = self.client.get(reverse("course_detail", args=["ART101"]))
        self.assertContains(page, "檢視 PDF")
        self.assertContains(page, "下載 PDF")
        self.assertContains(page, 'target="_blank"')

        preview = self.client.get(reverse("course_syllabus", args=["ART101"]))
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview["Content-Type"], "application/pdf")
        self.assertIn("inline", preview["Content-Disposition"])

        download = self.client.get(reverse("course_syllabus", args=["ART101"]) + "?download=1")
        self.assertIn("attachment", download["Content-Disposition"])

        missing = self.client.get(reverse("course_syllabus", args=["CS101"]))
        self.assertEqual(missing.status_code, 404)

    def test_admin_rejects_a_non_pdf_syllabus(self):
        from timetable.admin import CourseAdminForm
        from timetable.models import Course

        course = Course.objects.get(pk="ART101")
        form = CourseAdminForm(
            data={
                "course_id": course.course_id,
                "name": course.name,
                "teacher": course.teacher,
                "weekday": course.weekday,
                "start_period": course.start_period,
                "end_period": course.end_period,
                "credits": course.credits,
                "course_type": course.course_type,
                "module": course.module,
                "target_class": course.target_class,
                "total_quota": course.total_quota,
                "enrolled_count": course.enrolled_count,
            },
            files={"syllabus": SimpleUploadedFile("notes.txt", b"not a pdf", content_type="text/plain")},
            instance=course,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("PDF", form.errors["syllabus"][0])


class CourseListHeaderTests(TestCase):
    def test_course_code_and_credit_headers_stay_in_order(self):
        response = self.client.get(reverse("course_list"))
        html = response.content.decode()
        self.assertLess(html.find(">課程編號<"), html.find(">課程名稱<"))
        self.assertLess(html.find(">學分<"), html.find(">類型<"))
        self.assertNotIn(">狀態<", html)

    def test_invalid_weekday_filter_does_not_crash(self):
        response = self.client.get(reverse("course_list"), {"weekday": "abc"})
        self.assertEqual(response.status_code, 200)

    def test_favorites_table_matches_the_course_list_columns(self):
        user = User.objects.create_user(username="fav-student", password="password-1a")
        course_store.ensure_seeded()
        course_store.add_favorite(str(user.pk), "ART101")
        self.client.force_login(user)
        response = self.client.get(reverse("favorites"))
        html = response.content.decode()
        self.assertIn("course-list-table", html)
        self.assertLess(html.find(">課程編號<"), html.find(">課程名稱<"))
        self.assertLess(html.find(">名額<"), html.find(">操作<"))
        self.assertNotIn(">狀態<", html)
        self.assertContains(response, "選課")
        self.assertContains(response, "詳情")
        self.assertContains(response, "取消收藏")


class HomepageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", password="password-1a")
        self.client.force_login(self.user)

    def test_homepage_uses_balanced_summary_and_keeps_timetable(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("我的課表總覽", html)
        self.assertIn("本週課程表", html)
        self.assertIn("home-summary", html)
        self.assertIn("查看畢業進度", html)
        self.assertNotIn("overview-score", html)

    def test_period_ten_without_time_is_blank(self):
        response = self.client.get(reverse("index"))
        schedule = {row["period"]: row["time"] for row in response.context["weekly_schedule"]}
        self.assertEqual(schedule[10], "")
        self.assertEqual(schedule[1], "08:10–09:00")
        self.assertEqual(schedule[9], "17:15–18:05")
        self.assertEqual(schedule[11], "18:30–19:15")
        self.assertNotIn("待確認", response.content.decode())

    def test_export_payload_uses_the_signed_in_timetable(self):
        course_store.ensure_seeded()
        enrolled, _message = course_store.enroll_course(str(self.user.pk), "CS101")
        self.assertTrue(enrolled)
        response = self.client.get(reverse("index"))
        payload = response.context["export_payload"]
        self.assertEqual(payload["username"], "student")
        self.assertEqual(payload["periods"][9]["period"], 10)
        self.assertEqual(payload["periods"][9]["time"], "")
        self.assertEqual(payload["periods"][0]["time"], "08:10–09:00")
        self.assertEqual([course["course_id"] for course in payload["courses"]], ["CS101"])
        self.assertContains(response, "匯出課表")
        self.assertContains(response, "timetable-export.js")
        self.assertContains(response, "data-confirm=")
        self.assertNotContains(response, "onclick=\"return confirm")
        self.assertContains(response, "app-dialog")

    def test_feedback_message_uses_the_shared_alert(self):
        response = self.client.post(reverse("logout"), follow=True)
        self.assertContains(response, "alert-success")
        self.assertContains(response, "已登出")
        self.assertContains(response, "完成")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AccountSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="avatar-user", password="Old-password-1")
        self.other = User.objects.create_user(username="other-user", password="Old-password-1")
        self.client.force_login(self.user)

    def test_settings_keeps_password_and_removes_notification_controls(self):
        response = self.client.get(reverse("account_settings"))
        self.assertContains(response, "修改密碼")
        self.assertContains(response, "頭貼")
        self.assertLess(response.content.decode().find("修改密碼"), response.content.decode().find("頭貼"))
        self.assertNotContains(response, "本學期學分規則")
        self.assertNotContains(response, "主修模組")
        self.assertNotContains(response, "首頁提醒")
        self.assertNotContains(response, "notify_at_floor")

    def test_password_change_uses_django_hashing(self):
        wrong = self.client.post(reverse("account_settings"), {
            "action": "password",
            "old_password": "not-the-password",
            "new_password1": "New-password-2",
            "new_password2": "New-password-2",
        })
        self.assertEqual(wrong.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Old-password-1"))

        mismatch = self.client.post(reverse("account_settings"), {
            "action": "password",
            "old_password": "Old-password-1",
            "new_password1": "New-password-2",
            "new_password2": "New-password-3",
        })
        self.assertEqual(mismatch.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Old-password-1"))

        changed = self.client.post(reverse("account_settings"), {
            "action": "password",
            "old_password": "Old-password-1",
            "new_password1": "New-password-2",
            "new_password2": "New-password-2",
        }, follow=True)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-password-2"))
        self.assertTrue(self.user.password.startswith("pbkdf2_"))
        self.assertContains(changed, "密碼已更新")

    def test_avatar_upload_only_changes_the_signed_in_user(self):
        upload = SimpleUploadedFile("evil.svg", b"\x89PNG\r\n\x1a\n" + b"\x00" * 24, content_type="image/svg+xml")
        self.client.post(reverse("account_settings"), {
            "action": "avatar",
            "user_id": str(self.other.pk),
            "avatar": upload,
        }, follow=True)
        profile = StudentProfile.objects.get(pk=str(self.user.pk))
        self.assertTrue(profile.avatar.name.endswith(".png"))
        other = StudentProfile.objects.filter(pk=str(self.other.pk)).first()
        self.assertTrue(other is None or not other.avatar)

        rejected = self.client.post(reverse("account_settings"), {
            "action": "avatar",
            "avatar": SimpleUploadedFile("note.txt", b"not an image", content_type="text/plain"),
        })
        self.assertContains(rejected, "只接受")

        oversized = SimpleUploadedFile(
            "big.png",
            b"\x89PNG\r\n\x1a\n" + b"\x00" * (2 * 1024 * 1024),
            content_type="image/png",
        )
        too_big = self.client.post(reverse("account_settings"), {"action": "avatar", "avatar": oversized})
        self.assertContains(too_big, "2MB")

    def test_homepage_reminder_follows_the_system_rule(self):
        course_store.ensure_seeded()
        StudentProfile.objects.update_or_create(
            user_id=str(self.user.pk),
            defaults={
                "notify_at_floor": False,
                "notify_near_floor": False,
                "notify_at_limit": False,
            },
        )
        enrolled, _message = course_store.enroll_course(str(self.user.pk), "CS101")
        self.assertTrue(enrolled)
        response = self.client.get(reverse("index"))
        self.assertContains(response, "已達退選下限")


class SafetyRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="safety-user", password="Old-password-1")
        self.client.force_login(self.user)
        course_store.ensure_seeded()
        self.user_id = str(self.user.pk)

    def test_redirect_stays_inside_the_site(self):
        external = self.client.post(reverse("add_favorite"), {
            "course_id": "CS101",
            "next": "https://evil.example/phish",
        })
        self.assertEqual(external.status_code, 302)
        self.assertNotIn("evil.example", external.url)

        internal = self.client.post(reverse("add_favorite"), {
            "course_id": "CS102",
            "next": "/favorites/",
        })
        self.assertEqual(internal.url, "/favorites/")

    def test_repeat_enroll_does_not_consume_another_seat(self):
        from timetable.models import Course

        before = Course.objects.get(pk="CS201").enrolled_count
        first, _message = course_store.enroll_course(self.user_id, "CS201")
        second, message = course_store.enroll_course(self.user_id, "CS201")
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertIn("已經選過", message)
        self.assertEqual(Course.objects.get(pk="CS201").enrolled_count, before + 1)

        dropped, _message = course_store.drop_course(self.user_id, "CS201", force=True)
        self.assertTrue(dropped)
        self.assertEqual(Course.objects.get(pk="CS201").enrolled_count, before)

    def test_repeat_favorite_is_rejected(self):
        first, _message = course_store.add_favorite(self.user_id, "GE101")
        second, message = course_store.add_favorite(self.user_id, "GE101")
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertIn("已經收藏", message)


class AdminIdentityTests(TestCase):
    def test_staff_can_identify_users_and_students_cannot_enter_admin(self):
        student = User.objects.create_user(
            username="student2",
            password="Old-password-1",
            email="student2@example.com",
            first_name="王",
            last_name="小明",
        )
        staff = User.objects.create_superuser("boss", "boss@example.com", "Old-password-1")
        course_store.ensure_seeded()
        enrolled, _message = course_store.enroll_course(str(student.pk), "CS101")
        self.assertTrue(enrolled)

        self.client.force_login(student)
        denied = self.client.get("/admin/timetable/enrollment/")
        self.assertNotEqual(denied.status_code, 200)

        self.client.force_login(staff)
        page = self.client.get("/admin/timetable/enrollment/")
        self.assertContains(page, "student2")
        self.assertContains(page, "student2@example.com")
        self.assertContains(page, "王 小明")
        found = self.client.get("/admin/timetable/enrollment/?q=小明")
        self.assertContains(found, "student2")
        users = self.client.get("/admin/auth/user/")
        self.assertContains(users, "student2")
        self.assertNotContains(users, "password")

        home = self.client.get("/admin/")
        self.assertContains(home, "/admin/timetable/coursereview/")
        reviews = self.client.get("/admin/timetable/coursereview/")
        self.assertEqual(reviews.status_code, 200)


class StudyRecordSyncTests(TestCase):
    def test_admin_can_mark_a_record_passed_and_the_progress_page_follows(self):
        from timetable.models import Course, StudyRecord

        student = User.objects.create_user(username="record-student", password="Old-password-1")
        staff = User.objects.create_superuser("record-boss", "boss2@example.com", "Old-password-1")
        course_store.ensure_seeded()
        enrolled, _message = course_store.enroll_course(str(student.pk), "CS101")
        self.assertTrue(enrolled)
        course = Course.objects.get(pk="CS101")
        record = StudyRecord.objects.get(
            user_id=str(student.pk), course_code="CS101"
        )
        self.assertEqual(record.status, StudyRecord.STATUS_IN_PROGRESS)

        self.client.force_login(staff)
        listing = self.client.get("/admin/timetable/studyrecord/")
        self.assertContains(listing, "form-0-status")
        self.assertContains(listing, "已通過")
        updated = self.client.post(
            "/admin/timetable/studyrecord/",
            {
                "action": "mark_passed",
                "index": "0",
                "_selected_action": [str(record.pk)],
            },
            follow=True,
        )
        self.assertEqual(updated.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.status, StudyRecord.STATUS_PASSED)

        history = [
            row for row in course_store.get_study_history(str(student.pk))
            if row["course_code"] == "CS101"
        ]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["status"], StudyRecord.STATUS_PASSED)
        summary = course_store.get_graduation_summary(str(student.pk))
        self.assertEqual(summary["required"]["earned"], course.credits)
        self.assertEqual(summary["required"]["in_progress"], 0)

        self.client.force_login(student)
        progress = self.client.get(reverse("progress"))
        self.assertContains(progress, "已通過")

    def test_drop_removes_only_the_in_progress_record(self):
        from timetable.models import StudyRecord

        student = User.objects.create_user(username="drop-student", password="Old-password-1")
        course_store.ensure_seeded()
        user_id = str(student.pk)
        enrolled, _message = course_store.enroll_course(user_id, "CS102")
        self.assertTrue(enrolled)
        dropped, _message = course_store.drop_course(user_id, "CS102", force=True)
        self.assertTrue(dropped)
        self.assertFalse(
            StudyRecord.objects.filter(user_id=user_id, course_code="CS102").exists()
        )

        enrolled, _message = course_store.enroll_course(user_id, "CS103")
        self.assertTrue(enrolled)
        kept = StudyRecord.objects.get(user_id=user_id, course_code="CS103")
        kept.status = StudyRecord.STATUS_PASSED
        kept.save(update_fields=["status"])
        dropped, _message = course_store.drop_course(user_id, "CS103", force=True)
        self.assertTrue(dropped)
        kept.refresh_from_db()
        self.assertEqual(kept.status, StudyRecord.STATUS_PASSED)
