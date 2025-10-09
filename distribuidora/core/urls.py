from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('carrito/', views.carrito, name='carrito'),
    path('mis-compras/', views.mis_compras, name='mis_compras'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),  
    path('logout/', views.logout_view, name='logout'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('add_to_carrito/<int:producto_id>/', views.add_to_carrito, name='add_to_carrito'),
    path('remove_from_carrito/<int:item_id>/', views.remove_from_carrito, name='remove_from_carrito'),
    path('api/productos/', views.ProductoListAPIView.as_view(), name='producto_list_api'),
    path('checkout/', views.checkout, name='checkout'),  
]