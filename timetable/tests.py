import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from timetable.data_store import course_store
from timetable.models import Enrollment, StudentProfile


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

    def test_credits_over_the_personal_limit_can_still_be_enrolled(self):
        from timetable.models import UserCreditLimit

        UserCreditLimit.objects.update_or_create(
            user_id=self.user_id,
            defaults={"credit_floor": 0, "credit_limit": 3},
        )
        first, _message = course_store.enroll_course(self.user_id, "CS101")
        self.assertTrue(first)
        self.assertEqual(course_store.get_user_total_credits(self.user_id), 3)

        self.client.force_login(self.user)
        at_limit = self.client.get(reverse("index"))
        self.assertContains(at_limit, "超出的學分不一定能認列，請自行確認。")

        second, message = course_store.enroll_course(self.user_id, "CS102")
        self.assertTrue(second, message)
        self.assertIn("不一定能認列", message)
        self.assertEqual(course_store.get_user_total_credits(self.user_id), 6)

        allowed, preview = course_store.check_enrollment_eligibility(self.user_id, "CS103")
        self.assertTrue(allowed)
        self.assertIn("不一定都能認列", preview)

        home = self.client.get(reverse("index"))
        self.assertContains(home, "超過上限 3 學分。超出的學分不一定都能認列，請自行確認。")
        self.assertNotContains(home, "被上限擋住")
        listing = self.client.get(reverse("course_list"), {"keyword": "CS103"})
        self.assertContains(listing, "選課")
        self.assertNotContains(listing, "disabled title=\"超過學分上限")

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
        course_store.set_student_module(self.user_id, "資訊")
        response = self.client.get(reverse("progress"))
        self.assertContains(response, "<span>下限</span><strong>6</strong>")
        self.assertContains(response, "<span>上限</span><strong>12</strong>")
        self.assertNotContains(response, "<strong>不限制</strong>")

    def test_selected_module_shows_credits_and_warns_below_the_minimum(self):
        from timetable.models import ModuleCreditLimit, StudyRecord

        ModuleCreditLimit.objects.update_or_create(
            module="資訊", defaults={"min_credits": 3, "max_credits": 0}
        )
        course_store.set_student_module(self.user_id, "資訊")
        self.client.force_login(self.user)
        empty = self.client.get(reverse("progress"))
        self.assertContains(empty, "<span>上限</span><strong>不限制</strong>")
        self.assertContains(empty, "還差 3")
        self.assertNotContains(empty, ">金融</h3>")

        enrolled, _message = course_store.enroll_course(self.user_id, "CS301")
        self.assertTrue(enrolled)
        taking = self.client.get(reverse("progress"))
        self.assertContains(taking, "<span>正在修</span><strong>3</strong>")

        record = StudyRecord.objects.get(user_id=self.user_id, course_code="CS301")
        record.status = StudyRecord.STATUS_UNRECOGNIZED
        record.save(update_fields=["status"])
        skipped = self.client.get(reverse("progress"))
        self.assertContains(skipped, "不認列 3 學分")
        self.assertContains(skipped, "<span>正在修</span><strong>0</strong>")
        self.assertContains(skipped, "還差 3")

    def test_a_module_created_in_admin_can_be_chosen_and_limited(self):
        from timetable.models import Course, ModuleCreditLimit

        limit = ModuleCreditLimit(module="設計", min_credits=2, max_credits=4)
        limit.full_clean()
        limit.save()
        Course.objects.create(
            course_id="DS101",
            name="設計概論",
            teacher="設教授",
            weekday=5,
            start_period=6,
            end_period=8,
            credits=3,
            course_type="選修",
            module="設計",
            target_class="全校",
            total_quota=30,
        )
        Course.objects.create(
            course_id="DS102",
            name="設計進階",
            teacher="設教授",
            weekday=3,
            start_period=6,
            end_period=8,
            credits=3,
            course_type="選修",
            module="設計",
            target_class="全校",
            total_quota=30,
        )

        self.assertTrue(course_store.set_student_module(self.user_id, "設計"))
        self.assertFalse(course_store.set_student_module(self.user_id, "不存在"))
        self.client.force_login(self.user)
        page = self.client.get(reverse("progress"))
        self.assertContains(page, '<option value="設計" selected>設計</option>')
        self.assertContains(page, "<span>下限</span><strong>2</strong>")
        self.assertContains(page, "<span>上限</span><strong>4</strong>")
        self.assertContains(page, ">設計</h3>")
        self.assertNotContains(page, ">資訊</h3>")

        enrolled, message = course_store.enroll_course(self.user_id, "DS101")
        self.assertTrue(enrolled, message)
        blocked, message = course_store.enroll_course(self.user_id, "DS102")
        self.assertFalse(blocked)
        self.assertIn("設計模組學分上限", message)


class RegisterPageTests(TestCase):
    def test_register_sends_the_new_user_to_settings(self):
        response = self.client.post(reverse("register"), {
            "username": "new-student",
            "password1": "password-1a",
            "password2": "password-1a",
        })
        self.assertRedirects(response, reverse("account_settings"))
        page = self.client.get(reverse("account_settings"))
        self.assertContains(page, "請填寫姓名、學號與班級")

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

    def test_blocked_enroll_button_shows_the_reason_on_hover(self):
        user = User.objects.create_user(username="blocked-student", password="password-1a")
        course_store.ensure_seeded()
        enrolled, _message = course_store.enroll_course(str(user.pk), "GE101")
        self.assertTrue(enrolled)
        self.client.force_login(user)
        response = self.client.get(reverse("course_list"), {"keyword": "CS101"})
        self.assertContains(
            response,
            'disabled title="時間衝突：與「中國文學欣賞」（週一 第2-3節）衝堂"',
        )

    def test_enrolled_favorite_shows_a_drop_button(self):
        user = User.objects.create_user(username="fav-enrolled", password="password-1a")
        course_store.ensure_seeded()
        user_id = str(user.pk)
        enrolled, _message = course_store.enroll_course(user_id, "ART102")
        self.assertTrue(enrolled)
        course_store.add_favorite(user_id, "ART102")
        self.client.force_login(user)
        response = self.client.get(reverse("favorites"))
        self.assertContains(response, "退選")
        self.assertContains(response, reverse("drop_course"))
        self.assertNotContains(response, 'title="已選修"')


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

    def test_student_can_save_identity_once_and_keeps_the_student_number(self):
        course_store.ensure_seeded()
        home = self.client.get(reverse("index"))
        self.assertContains(home, "請填寫姓名、學號與班級")
        settings_page = self.client.get(reverse("account_settings"))
        self.assertContains(settings_page, "請填寫姓名、學號與班級")
        self.assertContains(settings_page, "資工一")

        invalid = self.client.post(reverse("account_settings"), {
            "action": "profile",
            "name": "林同學",
            "student_number": "ab12",
            "class_name": "資工一",
        })
        self.assertContains(invalid, "學號須為 5 到 12 碼英數")
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "")

        saved = self.client.post(reverse("account_settings"), {
            "action": "profile",
            "name": "林同學",
            "student_number": "a12345",
            "class_name": "資工一",
        }, follow=True)
        self.assertContains(saved, "已更新個人資料")
        self.assertNotContains(saved, "請填寫姓名、學號與班級")
        self.assertContains(saved, "學號如需更正，請聯絡管理員")
        self.user.refresh_from_db()
        profile = StudentProfile.objects.get(pk=str(self.user.pk))
        self.assertEqual(self.user.first_name, "林同學")
        self.assertEqual(self.user.last_name, "")
        self.assertEqual(profile.student_number, "A12345")
        self.assertEqual(profile.class_name, "資工一")

        changed = self.client.post(reverse("account_settings"), {
            "action": "profile",
            "name": "林小同學",
            "student_number": "B99999",
            "class_name": "資工二",
        }, follow=True)
        self.assertContains(changed, "已更新個人資料")
        self.user.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(self.user.first_name, "林小同學")
        self.assertEqual(profile.student_number, "A12345")
        self.assertEqual(profile.class_name, "資工二")
        done = self.client.get(reverse("index"))
        self.assertNotContains(done, "請填寫姓名、學號與班級")

    def test_student_number_must_be_unique(self):
        StudentProfile.objects.create(user_id=str(self.other.pk), student_number="A12345")
        response = self.client.post(reverse("account_settings"), {
            "action": "profile",
            "name": "林同學",
            "student_number": "a12345",
            "class_name": "資工一",
        })
        self.assertContains(response, "這個學號已經有人使用")
        self.assertFalse(StudentProfile.objects.filter(user_id=str(self.user.pk), student_number="A12345").exists())

    def test_selected_class_adds_required_courses_that_cannot_be_dropped(self):
        course_store.ensure_seeded()
        saved = self.client.post(reverse("account_settings"), {
            "action": "profile",
            "name": "林同學",
            "student_number": "A12345",
            "class_name": "資工一",
        }, follow=True)
        self.assertContains(saved, "必修課程已加入課表")
        user_id = str(self.user.pk)
        for course_id in ("CS101", "CS102", "CS103", "PE101", "PE102"):
            self.assertTrue(Enrollment.objects.filter(user_id=user_id, course_id=course_id).exists())
        self.assertFalse(Enrollment.objects.filter(user_id=user_id, course_id="CS201").exists())

        blocked, message = course_store.drop_course(user_id, "CS101")
        self.assertFalse(blocked)
        self.assertIn("不可退選", message)
        denied = self.client.post(reverse("drop_course"), {"course_id": "CS101", "next": "index"}, follow=True)
        self.assertContains(denied, "必修課程不可退選")
        self.assertTrue(Enrollment.objects.filter(user_id=user_id, course_id="CS101").exists())

        listing = self.client.get(reverse("course_list"))
        self.assertContains(listing, "不可退選")
        detail = self.client.get(reverse("course_detail", args=["CS101"]))
        self.assertContains(detail, "不可退選")
        self.assertNotContains(detail, "退選此課程")
        home = self.client.get(reverse("index"))
        self.assertContains(home, "程式設計(一)")
        self.assertContains(home, "不可退選")

        changed = self.client.post(reverse("account_settings"), {
            "action": "profile",
            "name": "林同學",
            "class_name": "資工二",
        }, follow=True)
        self.assertContains(changed, "已更新個人資料")
        self.assertTrue(Enrollment.objects.filter(user_id=user_id, course_id="CS201").exists())
        self.assertTrue(Enrollment.objects.filter(user_id=user_id, course_id="CS101").exists())
        dropped, _message = course_store.drop_course(user_id, "CS101")
        self.assertTrue(dropped)
        still_locked, message = course_store.drop_course(user_id, "CS202")
        self.assertFalse(still_locked)
        self.assertIn("不可退選", message)

    def test_settings_page_uses_the_profile_layout(self):
        response = self.client.get(reverse("account_settings"))
        self.assertContains(response, "帳號（唯讀）")
        self.assertContains(response, "請輸入姓名")
        self.assertContains(response, "儲存個人資料")
        self.assertContains(response, "頭貼設定")
        self.assertContains(response, "上傳圖片")
        page = response.content.decode()
        self.assertLess(page.find("個人資料"), page.find("修改密碼"))
        self.assertLess(page.find("修改密碼"), page.find("頭貼設定"))

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

    def test_admin_can_correct_a_student_number_and_rejects_duplicates(self):
        student = User.objects.create_user(username="id-student", password="Old-password-1")
        other = User.objects.create_user(username="other-student", password="Old-password-1")
        StudentProfile.objects.create(user_id=str(student.pk), student_number="A12345", class_name="資工一")
        StudentProfile.objects.create(user_id=str(other.pk), student_number="B12345")
        staff = User.objects.create_superuser("id-boss", "id-boss@example.com", "Old-password-1")
        course_store.ensure_seeded()
        self.client.force_login(staff)

        listing = self.client.get("/admin/timetable/studentprofile/")
        self.assertContains(listing, "A12345")
        self.assertContains(listing, "資工一")
        found = self.client.get("/admin/timetable/studentprofile/?q=A12345")
        self.assertContains(found, "id-student")

        duplicate = self.client.post(
            f"/admin/timetable/studentprofile/{student.pk}/change/",
            {
                "name": "王小明",
                "student_number": "b12345",
                "class_name": "資工二",
                "module": "",
            },
        )
        self.assertContains(duplicate, "這個學號已經由帳號 other-student 使用")
        student.refresh_from_db()
        self.assertEqual(student.first_name, "")

        updated = self.client.post(
            f"/admin/timetable/studentprofile/{student.pk}/change/",
            {
                "name": "王小明",
                "student_number": "C12345",
                "class_name": "資工二",
                "module": "",
            },
            follow=True,
        )
        self.assertEqual(updated.status_code, 200)
        student.refresh_from_db()
        profile = StudentProfile.objects.get(pk=str(student.pk))
        self.assertEqual(student.first_name, "王小明")
        self.assertEqual(profile.student_number, "C12345")
        self.assertEqual(profile.class_name, "資工二")
        self.assertTrue(Enrollment.objects.filter(user_id=str(student.pk), course_id="CS201").exists())
        self.assertFalse(Enrollment.objects.filter(user_id=str(student.pk), course_id="CS101").exists())
        roster = self.client.get("/admin/timetable/enrollment/")
        self.assertContains(roster, "學生不可退選")

    def test_new_required_course_is_added_to_that_class(self):
        student = User.objects.create_user(username="class-student", password="Old-password-1")
        StudentProfile.objects.create(
            user_id=str(student.pk),
            class_name="資工一",
            student_number="A11111",
        )
        staff = User.objects.create_superuser("course-boss", "course-boss@example.com", "Old-password-1")
        self.client.force_login(staff)
        created = self.client.post("/admin/timetable/course/add/", {
            "course_id": "CS109",
            "name": "計算機組織",
            "teacher": "新教授",
            "course_type": "必修",
            "module": "",
            "target_class": "資工一",
            "weekday": "3",
            "start_period": "2",
            "end_period": "4",
            "credits": "3",
            "total_quota": "40",
        })
        self.assertEqual(created.status_code, 302, created.content.decode()[:500] if created.status_code != 302 else "")
        self.assertTrue(
            Enrollment.objects.filter(user_id=str(student.pk), course_id="CS109").exists()
        )
        rejected = self.client.post("/admin/timetable/course/add/", {
            "course_id": "../secret",
            "name": "不該建立",
            "teacher": "新教授",
            "course_type": "123",
            "module": "",
            "target_class": "資工一",
            "weekday": "1",
            "start_period": "2",
            "end_period": "3",
            "credits": "2",
            "total_quota": "20",
        })
        self.assertEqual(rejected.status_code, 200)
        self.assertContains(rejected, "課程編號只能使用英數")
        self.assertContains(rejected, "id_course_type_error")
        self.assertFalse(Enrollment.objects.filter(course_id="../secret").exists())

    def test_module_and_class_are_chosen_from_admin_lists(self):
        course_store.ensure_seeded()
        staff = User.objects.create_superuser("class-boss", "class-boss@example.com", "Old-password-1")
        student = User.objects.create_user(username="class-picker", password="Old-password-1")
        self.client.force_login(staff)
        added = self.client.post("/admin/timetable/schoolclass/add/", {"name": "資工四"})
        self.assertEqual(added.status_code, 302)
        blocked = self.client.post("/admin/timetable/schoolclass/add/", {"name": "全校"})
        self.assertContains(blocked, "不用另外建班級")
        form = self.client.get("/admin/timetable/course/add/")
        self.assertContains(form, "資工四")
        self.assertContains(form, "不屬於模組")
        self.assertContains(form, "全校")
        rejected = self.client.post("/admin/timetable/course/add/", {
            "course_id": "CS401",
            "name": "不該建立",
            "teacher": "新教授",
            "course_type": "選修",
            "module": "沒有這個模組",
            "target_class": "沒有這班",
            "weekday": "1",
            "start_period": "1",
            "end_period": "2",
            "credits": "2",
            "total_quota": "20",
        })
        self.assertContains(rejected, "請選擇已建立的模組")
        self.assertContains(rejected, "請選擇已建立的班級")
        self.client.force_login(student)
        settings_page = self.client.get(reverse("account_settings"))
        self.assertContains(settings_page, "資工四")

    def test_course_form_can_create_a_class(self):
        from timetable.models import Course, SchoolClass

        course_store.ensure_seeded()
        staff = User.objects.create_superuser("new-class-boss", "new-class@example.com", "Old-password-1")
        self.client.force_login(staff)
        form = self.client.get("/admin/timetable/course/add/")
        self.assertContains(form, "新增班級")
        created = self.client.post("/admin/timetable/course/add/", {
            "course_id": "CS401",
            "name": "新班級課程",
            "teacher": "新教授",
            "course_type": "選修",
            "module": "",
            "target_class": "",
            "new_class": "資工四",
            "weekday": "1",
            "start_period": "1",
            "end_period": "2",
            "credits": "2",
            "total_quota": "20",
        })
        self.assertEqual(created.status_code, 302)
        self.assertTrue(SchoolClass.objects.filter(name="資工四").exists())
        self.assertEqual(Course.objects.get(pk="CS401").target_class, "資工四")
        rejected = self.client.post("/admin/timetable/course/add/", {
            "course_id": "CS402",
            "name": "不該用全校當新班級",
            "teacher": "新教授",
            "course_type": "選修",
            "module": "",
            "target_class": "",
            "new_class": "全校",
            "weekday": "1",
            "start_period": "1",
            "end_period": "2",
            "credits": "2",
            "total_quota": "20",
        })
        self.assertContains(rejected, "不用另外建立")

    def test_new_required_course_drops_a_conflicting_elective(self):
        course_store.ensure_seeded()
        student = User.objects.create_user(username="clash-student", password="Old-password-1")
        user_id = str(student.pk)
        StudentProfile.objects.create(
            user_id=user_id,
            class_name="資工一",
            student_number="A22222",
        )
        course_store.assign_required_courses(user_id)
        enrolled, message = course_store.enroll_course(user_id, "GE202")
        self.assertTrue(enrolled, message)
        staff = User.objects.create_superuser("clash-boss", "clash-boss@example.com", "Old-password-1")
        self.client.force_login(staff)
        created = self.client.post("/admin/timetable/course/add/", {
            "course_id": "CS110",
            "name": "必修衝堂",
            "teacher": "新教授",
            "course_type": "必修",
            "module": "",
            "target_class": "資工一",
            "weekday": "2",
            "start_period": "6",
            "end_period": "7",
            "credits": "2",
            "total_quota": "40",
        }, follow=True)
        self.assertContains(created, "CS110")
        self.assertFalse(Enrollment.objects.filter(user_id=user_id, course_id="GE202").exists())
        self.assertTrue(Enrollment.objects.filter(user_id=user_id, course_id="CS110").exists())
        self.client.force_login(student)
        home = self.client.get(reverse("index"))
        self.assertContains(home, "必修衝堂")
        self.assertContains(home, "已退選")
        self.assertNotContains(home, 'value="GE202"')

    def test_two_required_courses_in_the_same_slot_stay_visible(self):
        course_store.ensure_seeded()
        student = User.objects.create_user(username="double-student", password="Old-password-1")
        user_id = str(student.pk)
        StudentProfile.objects.create(
            user_id=user_id,
            class_name="資工一",
            student_number="A33333",
        )
        staff = User.objects.create_superuser("double-boss", "double-boss@example.com", "Old-password-1")
        self.client.force_login(staff)
        course_fields = {
            "teacher": "新教授",
            "course_type": "必修",
            "module": "",
            "target_class": "資工一",
            "weekday": "2",
            "start_period": "6",
            "end_period": "7",
            "credits": "2",
            "total_quota": "40",
        }
        first = self.client.post("/admin/timetable/course/add/", {
            "course_id": "CS110",
            "name": "必修甲",
            **course_fields,
        })
        self.assertEqual(first.status_code, 302)
        second = self.client.post("/admin/timetable/course/add/", {
            "course_id": "CS111",
            "name": "必修乙",
            **course_fields,
        }, follow=True)
        self.assertContains(second, "CS111")
        self.assertTrue(Enrollment.objects.filter(user_id=user_id, course_id="CS110").exists())
        self.assertTrue(Enrollment.objects.filter(user_id=user_id, course_id="CS111").exists())
        self.client.force_login(student)
        home = self.client.get(reverse("index"))
        self.assertContains(home, "必修甲")
        self.assertContains(home, "必修乙")
        self.assertContains(home, "is-shared")
        self.assertContains(home, "上課時間重疊")


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

    def test_unrecognized_pass_is_not_counted_as_earned(self):
        from timetable.models import StudyRecord

        student = User.objects.create_user(username="skip-credit", password="Old-password-1")
        staff = User.objects.create_superuser("skip-boss", "skip@example.com", "Old-password-1")
        course_store.ensure_seeded()
        user_id = str(student.pk)
        course_store.enroll_course(user_id, "CS101")
        record = StudyRecord.objects.get(user_id=user_id, course_code="CS101")
        record.status = StudyRecord.STATUS_PASSED
        record.save(update_fields=["status"])
        course_store.enroll_course(user_id, "CS102")
        extra = StudyRecord.objects.get(user_id=user_id, course_code="CS102")

        self.client.force_login(staff)
        marked = self.client.post(
            "/admin/timetable/studyrecord/",
            {
                "action": "mark_unrecognized",
                "index": "0",
                "_selected_action": [str(extra.pk)],
            },
            follow=True,
        )
        self.assertEqual(marked.status_code, 200)
        extra.refresh_from_db()
        self.assertEqual(extra.status, StudyRecord.STATUS_UNRECOGNIZED)

        summary = course_store.get_graduation_summary(user_id)
        self.assertEqual(summary["required"]["earned"], 3)
        self.assertEqual(summary["unrecognized_total"], 3)
        self.assertEqual(summary["in_progress_total"], 0)

        self.client.force_login(student)
        progress = self.client.get(reverse("progress"))
        self.assertContains(progress, "已過但不認列")
        filtered = self.client.get(reverse("progress"), {"status": "unrecognized"})
        self.assertContains(filtered, "CS102")
        self.assertNotContains(filtered, "CS101")
