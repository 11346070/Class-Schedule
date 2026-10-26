"""
URL configuration for timetable_project project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('timetable.urls')),
]

admin.site.site_header = '個人課表維護系統後台'
admin.site.site_title = '課表後台'
admin.site.index_title = '管理首頁'
