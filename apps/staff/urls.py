from django.urls import path
from . import views

app_name = 'staff'
urlpatterns = [
    path('', views.directory, name='directory'),
    path('me/', views.dashboard, name='dashboard'),
    path('me/profile/', views.edit_profile, name='edit_profile'),
    path('me/work/new/', views.edit_item, name='new_item'),
    path('me/work/<int:pk>/edit/', views.edit_item, name='edit_item'),
    path('me/work/<int:pk>/delete/', views.delete_item, name='delete_item'),
    path('<slug:slug>/', views.profile, name='profile'),
    path('<slug:slug>/work/<int:pk>/', views.item, name='item'),
]
