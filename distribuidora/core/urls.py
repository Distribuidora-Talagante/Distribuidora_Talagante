from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('carrito/', views.carrito, name='carrito'),  # Nueva ruta para carrito
    path('mis-compras/', views.mis_compras, name='mis_compras'),  # Ruta para mis compras
    path('login/', views.login_view, name='login'),  # Vista básica para login
    path('logout/', views.logout_view, name='logout'),  # Vista para logout
    path('admin-panel/', views.admin_panel, name='admin_panel'),  # Panel admin
    path('add_to_carrito/<int:producto_id>/', views.add_to_carrito, name='add_to_carrito'),
]