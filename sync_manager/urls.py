
from django.urls import path
from . import views

app_name = 'sync_manager'

urlpatterns = [
    # OpenVPN 账号管理
    path('', views.openvpn_dashboard, name='dashboard'),
    path('create/', views.create_account, name='create_account'),
    path('status/', views.account_status, name='account_status'),
    path('download/', views.download_config, name='download_config'),
    path('renew/', views.renew_account, name='renew_account'),
    path('delete/', views.delete_account, name='delete_account'),
]
