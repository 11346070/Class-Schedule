from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from timetable.data_store import course_store


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
