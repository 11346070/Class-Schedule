"""
Views - 處理所有網頁請求與選課操作
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from .data_store import course_store


def get_user_id(request):
    """
    取得使用者 ID
    使用 Session 識別不同使用者
    """
    if 'user_id' not in request.session:
        # 使用 session_key 作為 user_id
        if not request.session.session_key:
            request.session.create()
        request.session['user_id'] = request.session.session_key
    
    return request.session['user_id']


@require_http_methods(["GET"])
def index(request):
    """首頁 - 顯示課表總覽"""
    user_id = get_user_id(request)
    enrolled_courses = course_store.get_user_enrollments(user_id)
    total_credits = course_store.get_user_total_credits(user_id)
    
    # 建立每週課表（簡化版，直接給模板使用）
    weekly_schedule = []
    for period in range(1, 14):
        period_row = {'period': period, 'courses': []}
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
        'enrolled_count': len(enrolled_courses),
        'weekly_schedule': weekly_schedule,
        'weekdays': [
            (1, '週一'), (2, '週二'), (3, '週三'),
            (4, '週四'), (5, '週五'), (6, '週六'), (7, '週日')
        ],
        'periods': range(1, 14),
    }
    
    return render(request, 'index.html', context)


@require_http_methods(["GET"])
def course_list(request):
    """課程清單頁 - 顯示所有課程並支援搜尋"""
    user_id = get_user_id(request)
    
    # 取得搜尋參數
    keyword = request.GET.get('keyword', '').strip()
    course_type = request.GET.get('course_type', '').strip()
    weekday = int(request.GET.get('weekday', 0))
    
    # 搜尋課程
    courses = course_store.search_courses(keyword, course_type, weekday)
    
    # 標記使用者已選的課程
    enrolled_course_ids = {c.course_id for c in course_store.get_user_enrollments(user_id)}
    
    courses_with_status = []
    for course in courses:
        course_dict = course.to_dict()
        course_dict['is_enrolled'] = course.course_id in enrolled_course_ids
        courses_with_status.append(course_dict)
    
    context = {
        'courses': courses_with_status,
        'keyword': keyword,
        'course_type': course_type,
        'weekday': weekday,
        'course_types': ['必修', '選修', '通識'],
        'weekdays': [
            (1, '週一'), (2, '週二'), (3, '週三'),
            (4, '週四'), (5, '週五'), (6, '週六'), (7, '週日')
        ],
    }
    
    return render(request, 'course_list.html', context)


@require_http_methods(["GET"])
def my_courses(request):
    """我的課表頁 - 顯示已選課程"""
    user_id = get_user_id(request)
    enrolled_courses = course_store.get_user_enrollments(user_id)
    total_credits = course_store.get_user_total_credits(user_id)
    
    # 按星期和節次排序
    enrolled_courses.sort(key=lambda c: (c.weekday, c.start_period))
    
    courses_dict = [course.to_dict() for course in enrolled_courses]
    
    context = {
        'courses': courses_dict,
        'total_credits': total_credits,
        'course_count': len(enrolled_courses),
    }
    
    return render(request, 'my_courses.html', context)


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
    next_url = request.POST.get('next', 'course_list')
    return redirect(next_url)


@require_POST
def drop_course(request):
    """退選課程操作"""
    user_id = get_user_id(request)
    course_id = request.POST.get('course_id', '').strip()
    
    if not course_id:
        messages.error(request, '課程編號不得為空')
        return redirect('my_courses')
    
    # 執行退選
    success, message = course_store.drop_course(user_id, course_id)
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    # 重導回我的課表或來源頁面
    next_url = request.POST.get('next', 'my_courses')
    return redirect(next_url)


@require_http_methods(["GET"])
def course_detail(request, course_id):
    """課程詳細資訊頁"""
    user_id = get_user_id(request)
    course = course_store.get_course(course_id)
    
    if not course:
        messages.error(request, '課程不存在')
        return redirect('course_list')
    
    is_enrolled = course_store.is_user_enrolled(user_id, course_id)
    
    # 檢查是否有時間衝突
    conflict_course = None
    if not is_enrolled:
        enrolled_courses = course_store.get_user_enrollments(user_id)
        for existing_course in enrolled_courses:
            if existing_course.weekday == course.weekday:
                if course_store._periods_overlap(
                    existing_course.start_period, existing_course.end_period,
                    course.start_period, course.end_period
                ):
                    conflict_course = existing_course
                    break
    
    course_dict = course.to_dict()
    
    context = {
        'course': course_dict,
        'is_enrolled': is_enrolled,
        'conflict_course': conflict_course.to_dict() if conflict_course else None,
    }
    
    return render(request, 'course_detail.html', context)


@require_http_methods(["GET"])
def system_info(request):
    """系統資訊頁 - 顯示系統狀態及說明"""
    total_courses = len(course_store.get_all_courses())
    total_users = len(course_store.user_enrollments)
    
    # 統計各類型課程
    course_types_count = {}
    for course in course_store.get_all_courses():
        course_types_count[course.course_type] = course_types_count.get(course.course_type, 0) + 1
    
    context = {
        'total_courses': total_courses,
        'total_users': total_users,
        'course_types_count': course_types_count,
    }
    
    return render(request, 'system_info.html', context)
