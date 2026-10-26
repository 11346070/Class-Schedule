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
    
    # 收藏清單
    path('favorites/', views.favorites, name='favorites'),
    
    # 選課操作
    path('enroll/', views.enroll_course, name='enroll_course'),
    
    # 退選操作
    path('drop/', views.drop_course, name='drop_course'),
    
    # 收藏操作
    path('favorites/add/', views.add_favorite, name='add_favorite'),
    
    # 取消收藏操作
    path('favorites/remove/', views.remove_favorite, name='remove_favorite'),
]
