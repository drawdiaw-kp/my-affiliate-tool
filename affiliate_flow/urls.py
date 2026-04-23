from django.contrib import admin
from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('generate-content/', views.generate_content, name='generate_content'),
    path('tts/', views.text_to_speech, name='tts'),
    path('get-history/', views.get_history, name='get_history'), 
    path('clear-history/', views.clear_history, name='clear_history'),
    path('delete-item/<int:item_id>/', views.delete_history_item, name='delete_item'),
    path('generate-video/', views.generate_video, name='generate_video'),
]

# อนุญาตให้ระบบอ่านไฟล์จากโฟลเดอร์ media ในขณะที่กำลังรันเซิร์ฟเวอร์จำลอง
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)