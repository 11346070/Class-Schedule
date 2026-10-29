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

    # 修課進度
    path('progress/', views.progress, name='progress'),
    
    # 課程詳細資訊
    path('courses/<str:course_id>/', views.course_detail, name='course_detail'),
    
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

    # 登入／註冊（登入狀態存在 SQLite session，不使用 sessions 資料夾）
    path('login/', views.StyledLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
]
