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


class CourseListHeaderTests(TestCase):
    def test_course_code_and_credit_headers_stay_in_order(self):
        response = self.client.get(reverse("course_list"))
        html = response.content.decode()
        self.assertLess(html.find(">課程編號<"), html.find(">課程名稱<"))
        self.assertLess(html.find(">學分<"), html.find(">類型<"))


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
