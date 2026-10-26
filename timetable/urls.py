"""
URL routing for timetable app
"""

from django.urls import path
from . import views

urlpatterns = [
    # 首頁
    path('', views.index, name='index'),
    
    # 課程清單
    path('courses/', views.course_list, name='course_list'),
    
    # 課程詳細資訊
    path('courses/<str:course_id>/', views.course_detail, name='course_detail'),
    
    # 我的課表
    path('my-courses/', views.my_courses, name='my_courses'),
    
    # 選課操作
    path('enroll/', views.enroll_course, name='enroll_course'),
    
    # 退選操作
    path('drop/', views.drop_course, name='drop_course'),
    
    # 系統資訊
    path('system-info/', views.system_info, name='system_info'),
]
