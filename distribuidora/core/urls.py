from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views  # Importa el módulo views de core
from django.urls import path
from . import views
from .views import CrearOrdenView
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
    path('admin_home/', views.admin_home, name='admin_home'),
    path('admin/producto/crear/', views.producto_create, name='producto_create'),
    path('admin/producto/editar/<int:producto_id>/', views.producto_update, name='producto_update'),
    path('admin/producto/eliminar/<int:producto_id>/', views.producto_delete, name='producto_delete'),
    path('admin/productos/', views.producto_list, name='producto_list'),
    path('admin/orden/<int:orden_id>/', views.orden_detail, name='orden_detail'),
    path('crear-orden/', CrearOrdenView.as_view(), name='crear_orden'),
    #path('probar-orden/', ProbarOrdenView.as_view(), name='probar_orden'),
    path('test-endpoint/', views.test_endpoint_view, name='test_endpoint'),
    path('admin/orden/<int:orden_id>/actualizar/', views.update_orden_status, name='update_orden_status'),
    path('mis-compras/', views.mis_compras, name='mis_compras'),
]