"""
Views - 處理所有網頁請求與選課操作
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from .data_store import course_store
from .forms import (
    AvatarUploadForm,
    RegisterForm,
    StyledAuthenticationForm,
    StyledPasswordChangeForm,
)


class StyledLoginView(LoginView):
    template_name = "login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "已登出")
    return redirect("login")


def register(request):
    """註冊帳號，成功後直接登入。"""
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "註冊成功，已為你登入")
            return redirect("index")
    else:
        form = RegisterForm()

    return render(request, "register.html", {"form": form})


def get_user_id(request):
    """已登入使用者以帳號主鍵當選課識別，資料存在 SQLite。"""
    if not request.user.is_authenticated:
        return ""
    return str(request.user.pk)


def courses_with_enroll_status(user_id, courses, enrolled_course_ids, authenticated=True):
    """為清單上的每門課附上是否已選，以及選不了的原因。"""
    courses_with_status = []
    for course in courses:
        course_dict = course.to_dict()
        course_dict["is_enrolled"] = course.course_id in enrolled_course_ids
        if not authenticated:
            course_dict["can_enroll"] = False
            course_dict["enroll_message"] = "請先登入"
        elif course_dict["is_enrolled"]:
            course_dict["can_enroll"] = False
            course_dict["enroll_message"] = "已選修"
        else:
            can_enroll, message = course_store.check_enrollment_eligibility(
                user_id, course.course_id
            )
            course_dict["can_enroll"] = can_enroll
            course_dict["enroll_message"] = message
        courses_with_status.append(course_dict)
    summaries = course_store.get_review_summaries(
        [course.course_id for course in courses]
    )
    for course_dict in courses_with_status:
        course_dict["review_summary"] = summaries.get(course_dict["course_id"])
    return courses_with_status


def redirect_after_action(request, default='course_list'):
    """
    依表單 next 參數重導向。
    course_detail 需帶 course_id，其餘可為 URL 名稱或路徑。
    """
    next_url = (request.POST.get('next') or default).strip()
    course_id = request.POST.get('course_id', '').strip()

    if next_url == 'course_detail' and course_id:
        return redirect('course_detail', course_id=course_id)

    try:
        return redirect(reverse(next_url))
    except NoReverseMatch:
        pass

    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect(default)


PERIOD_TIMES = {
    1: "08:10–09:00",
    2: "09:10–10:00",
    3: "10:10–11:00",
    4: "11:10–12:00",
    5: "13:30–14:20",
    6: "14:25–15:15",
    7: "15:25–16:15",
    8: "16:20–17:10",
    9: "17:15–18:05",
    10: "",
    11: "18:30–19:15",
    12: "19:20–20:05",
    13: "20:15–21:00",
}


@login_required
@require_http_methods(["GET"])
def index(request):
    """首頁 - 顯示課表總覽"""
    user_id = get_user_id(request)
    enrolled_courses = course_store.get_user_enrollments(user_id)
    total_credits = course_store.get_user_total_credits(user_id)
    credit_limit = course_store.get_user_credit_limit(user_id)
    credit_floor = course_store.get_user_credit_floor(user_id)
    
    # 建立每週課表（簡化版，直接給模板使用）
    weekly_schedule = []
    for period in range(1, 14):
        period_row = {
            'period': period,
            'time': PERIOD_TIMES.get(period, ''),
            'courses': [],
        }
        for weekday in range(1, 8):
            # 找出這個時段的課程
            period_course = None
            for course in enrolled_courses:
                if (course.weekday == weekday and 
                    course.start_period <= period <= course.end_period):
                    # 只在開始節次顯示完整課程區塊
                    if course.start_period == period:
                        period_course = {
                            'course': course,
                            'rowspan': course.end_period - course.start_period + 1
                        }
                    else:
                        # 中間節次用特殊標記（CSS 會處理）
                        period_course = {'course': course, 'is_continuation': True}
                    break
            period_row['courses'].append(period_course)
        weekly_schedule.append(period_row)
    
    context = {
        'enrolled_courses': enrolled_courses,
        'total_credits': total_credits,
        'credit_limit': credit_limit,
        'credit_floor': credit_floor,
        'remaining_credits': max(credit_limit - total_credits, 0),
        'credit_percent': min(100, round(total_credits * 100 / credit_limit)) if credit_limit else 0,
        'floor_percent': min(100, round(credit_floor * 100 / credit_limit)) if credit_limit else 0,
        **course_store.get_notification_prefs(user_id),
        'enrolled_count': len(enrolled_courses),
        'weekly_schedule': weekly_schedule,
        'weekdays': [
            (1, '週一'), (2, '週二'), (3, '週三'),
            (4, '週四'), (5, '週五'), (6, '週六'), (7, '週日')
        ],
        'periods': range(1, 14),
        'module_limit_notes': course_store.get_module_limit_notes(user_id),
        'export_payload': {
            'username': request.user.username,
            'display_name': request.user.get_full_name() or request.user.username,
            'semester': '本學期',
            'periods': [
                {'period': period, 'time': PERIOD_TIMES.get(period, '')}
                for period in range(1, 14)
            ],
            'weekdays': ['週一', '週二', '週三', '週四', '週五', '週六', '週日'],
            'courses': [
                {
                    'course_id': course.course_id,
                    'name': course.name,
                    'teacher': course.teacher,
                    'weekday': course.weekday,
                    'start_period': course.start_period,
                    'end_period': course.end_period,
                    'credits': course.credits,
                    'course_type': course.course_type,
                    'target_class': course.target_class,
                }
                for course in enrolled_courses
            ],
        },
    }
    
    return render(request, 'index.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def account_settings(request):
    """個人設定：修改密碼與頭貼。主修模組改在修課進度設定。"""
    user_id = get_user_id(request)
    password_form = StyledPasswordChangeForm(request.user)
    avatar_form = AvatarUploadForm()

    if request.method == "POST" and request.POST.get("action") == "password":
        password_form = StyledPasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "密碼已更新")
            return redirect("account_settings")
    elif request.method == "POST" and request.POST.get("action") == "avatar":
        avatar_form = AvatarUploadForm(request.POST, request.FILES)
        if avatar_form.is_valid():
            course_store.set_avatar(user_id, avatar_form.cleaned_data["avatar"])
            messages.success(request, "已更新頭貼")
            return redirect("account_settings")
    elif request.method == "POST" and request.POST.get("action") == "module":
        if course_store.set_student_module(user_id, request.POST.get("module", "")):
            messages.success(request, "已更新主修模組")
        else:
            messages.error(request, "請選擇金融或資訊模組")
        return redirect("account_settings")

    return render(
        request,
        "account_settings.html",
        {
            "password_form": password_form,
            "avatar_form": avatar_form,
            "credit_limit": course_store.get_user_credit_limit(user_id),
            "credit_floor": course_store.get_user_credit_floor(user_id),
            "module": course_store.get_student_module(user_id),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def progress(request):
    """修課進度：畢業門檻、模組認列。"""
    user_id = get_user_id(request)
    if request.method == "POST":
        if course_store.set_student_module(user_id, request.POST.get("module", "")):
            messages.success(request, "已更新主修模組")
        else:
            messages.error(request, "請選擇金融或資訊模組")
        return redirect("progress")

    summary = course_store.get_graduation_summary(user_id)
    total = summary["total_required"] or 1
    summary["percent"] = min(100, round(summary["earned_total"] * 100 / total))

    history = course_store.get_study_history(user_id)
    semesters = sorted({row["semester"] for row in history}, reverse=True)
    status_filter = request.GET.get("status", "")
    semester_filter = request.GET.get("semester", "")
    if status_filter:
        history = [row for row in history if row["status"] == status_filter]
    if semester_filter:
        history = [row for row in history if row["semester"] == semester_filter]
    history_page = Paginator(history, 10).get_page(request.GET.get("page", 1))
    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "progress.html",
        {
            "summary": summary,
            "module_summary": course_store.get_module_summary(user_id),
            "module_limits": course_store.get_module_limit_rows(),
            "module_limit_notes": course_store.get_module_limit_notes(user_id),
            "history_page": history_page,
            "history_total": len(history),
            "semesters": semesters,
            "status_filter": status_filter,
            "semester_filter": semester_filter,
            "history_query": query_params.urlencode(),
        },
    )


@require_http_methods(["GET"])
def course_list(request):
    """課程清單頁 - 顯示所有課程並支援搜尋"""
    user_id = get_user_id(request)
    
    # 取得搜尋參數
    keyword = request.GET.get('keyword', '').strip()
    course_type = request.GET.get('course_type', '').strip()
    weekday = int(request.GET.get('weekday', 0))
    show_available = request.GET.get('show_available', '')
    
    # 搜尋課程
    courses = course_store.search_courses(keyword, course_type, weekday)
    
    # 篩選尚有名額的課程
    if show_available:
        courses = [c for c in courses if not c.is_full]
    
    # 標記使用者已選的課程和收藏的課程
    enrolled_course_ids = {c.course_id for c in course_store.get_user_enrollments(user_id)}
    favorited_course_ids = {c.course_id for c in course_store.get_user_favorites(user_id)}
    
    courses_with_status = courses_with_enroll_status(
        user_id,
        courses,
        enrolled_course_ids,
        authenticated=request.user.is_authenticated,
    )
    for course_dict in courses_with_status:
        course_dict['is_favorited'] = course_dict['course_id'] in favorited_course_ids

    paginator = Paginator(courses_with_status, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'courses': page_obj,
        'page_obj': page_obj,
        'querystring': query_params.urlencode(),
        'total_count': paginator.count,
        'keyword': keyword,
        'course_type': course_type,
        'weekday': weekday,
        'show_available': show_available,
        'course_types': ['必修', '選修', '通識'],
        'weekdays': [
            (1, '週一'), (2, '週二'), (3, '週三'),
            (4, '週四'), (5, '週五'), (6, '週六'), (7, '週日')
        ],
    }
    
    return render(request, 'course_list.html', context)


@login_required
@require_POST
def enroll_course(request):
    """選課操作"""
    user_id = get_user_id(request)
    course_id = request.POST.get('course_id', '').strip()
    
    if not course_id:
        messages.error(request, '課程編號不得為空')
        return redirect('course_list')
    
    # 執行選課
    success, message = course_store.enroll_course(user_id, course_id)
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    # 重導回課程清單或來源頁面
    return redirect_after_action(request, default='course_list')


@login_required
@require_POST
def drop_course(request):
    """退選課程操作"""
    user_id = get_user_id(request)
    course_id = request.POST.get('course_id', '').strip()
    
    if not course_id:
        messages.error(request, '課程編號不得為空')
        return redirect('index')
    
    # 執行退選
    success, message = course_store.drop_course(user_id, course_id)
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    # 重導回首頁或來源頁面
    return redirect_after_action(request, default='index')


@require_http_methods(["GET"])
def course_detail(request, course_id):
    """課程詳細資訊頁"""
    user_id = get_user_id(request)
    course = course_store.get_course(course_id)
    
    if not course:
        messages.error(request, '課程不存在')
        return redirect('course_list')
    
    authenticated = request.user.is_authenticated
    is_enrolled = authenticated and course_store.is_user_enrolled(user_id, course_id)
    is_favorited = authenticated and course_store.is_course_favorited(user_id, course_id)

    # 檢查是否有時間衝突
    conflict_course = None
    if authenticated and not is_enrolled:
        enrolled_courses = course_store.get_user_enrollments(user_id)
        for existing_course in enrolled_courses:
            if existing_course.weekday == course.weekday:
                if course_store._periods_overlap(
                    existing_course.start_period, existing_course.end_period,
                    course.start_period, course.end_period
                ):
                    conflict_course = existing_course
                    break

    if not authenticated:
        can_enroll, enroll_message = False, "請先登入後再選課"
    else:
        can_enroll, enroll_message = course_store.check_enrollment_eligibility(user_id, course_id)
    
    course_dict = course.to_dict()
    summaries = course_store.get_review_summaries([course_id])
    my_review = course_store.get_user_review(user_id, course_id) if authenticated else None

    context = {
        'course': course_dict,
        'is_enrolled': is_enrolled,
        'is_favorited': is_favorited,
        'conflict_course': conflict_course.to_dict() if conflict_course else None,
        'can_enroll': can_enroll,
        'enroll_message': enroll_message,
        'review_summary': summaries.get(course_id),
        'can_review': authenticated and course_store.can_review_course(user_id, course_id),
        'my_review': my_review,
    }
    
    return render(request, 'course_detail.html', context)


@login_required
@require_POST
def save_review(request, course_id):
    """儲存或更新課程評價。"""
    user_id = get_user_id(request)
    success, message = course_store.save_review(
        user_id,
        course_id,
        request.POST.get("homework", ""),
        request.POST.get("exam", ""),
    )
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect("course_detail", course_id=course_id)


@login_required
@require_POST
def add_favorite(request):
    """收藏課程操作"""
    user_id = get_user_id(request)
    course_id = request.POST.get('course_id', '').strip()
    
    if not course_id:
        messages.error(request, '課程編號不得為空')
        return redirect('course_list')
    
    # 執行收藏
    success, message = course_store.add_favorite(user_id, course_id)
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    # 重導回來源頁面
    return redirect_after_action(request, default='course_list')


@login_required
@require_POST
def remove_favorite(request):
    """取消收藏課程操作"""
    user_id = get_user_id(request)
    course_id = request.POST.get('course_id', '').strip()
    
    if not course_id:
        messages.error(request, '課程編號不得為空')
        return redirect('favorites')
    
    # 執行取消收藏
    success, message = course_store.remove_favorite(user_id, course_id)
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    # 重導回來源頁面
    return redirect_after_action(request, default='favorites')


@login_required
@require_http_methods(["GET"])
def favorites(request):
    """收藏清單頁"""
    user_id = get_user_id(request)
    favorited_courses = course_store.get_user_favorites(user_id)
    
    # 檢查每門課程的選課狀態及預檢結果
    enrolled_course_ids = {c.course_id for c in course_store.get_user_enrollments(user_id)}
    
    courses_with_status = courses_with_enroll_status(
        user_id, favorited_courses, enrolled_course_ids
    )
    
    context = {
        'courses': courses_with_status,
        'favorites_count': len(favorited_courses),
    }
    
    return render(request, 'favorites.html', context)

