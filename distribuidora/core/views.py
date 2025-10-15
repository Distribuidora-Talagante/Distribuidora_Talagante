from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Producto, Orden, Carrito, ItemCarrito, Perfil, ItemOrden
from .serializers import ProductoSerializer
from .forms import ProductoForm
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import ensure_csrf_cookie
import requests
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Carrito, ItemCarrito, Orden, ItemOrden, User
from .serializers import OrdenSerializer
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.core.paginator import Paginator
from .models import Producto, Orden
# Decorador para verificar si el usuario es superusuario
def is_superuser(user):
    return user.is_superuser


def home(request):
    return render(request, 'core/home.html', {'mensaje': 'Bienvenido a Distribuidora Talagante'})

@ensure_csrf_cookie
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_superuser:
                return redirect('admin_home')
            try:
                perfil = Perfil.objects.get(usuario=user)
                if perfil.es_admin:
                    return redirect('admin_panel')
                else:
                    return redirect('catalogo')
            except Perfil.DoesNotExist:
                return redirect('catalogo')
        else:
            return render(request, 'core/login.html', {'error': 'Credenciales inválidas'})
    return render(request, 'core/login.html')

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def producto_delete(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, f'Producto "{producto.nombre}" eliminado exitosamente.')
        return redirect('producto_list')
    return render(request, 'core/producto_confirm_delete.html', {'producto': producto})

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        nombre_completo = request.POST['nombre_completo']
        rut = request.POST['rut']
        telefono = request.POST.get('telefono', '')
        if User.objects.filter(username=username).exists():
            return render(request, 'core/login.html', {'reg_error': 'El usuario ya existe'})
        if Perfil.objects.filter(rut=rut).exists():
            return render(request, 'core/login.html', {'reg_error': 'El RUT ya está registrado'})
        try:
            user = User.objects.create_user(username=username, password=password)
            perfil = Perfil.objects.create(
                usuario=user,
                nombre_completo=nombre_completo,
                rut=rut,
                telefono=telefono,
                es_admin=False
            )
            login(request, user)
            return redirect('catalogo')
        except ValidationError as e:
            return render(request, 'core/login.html', {'reg_error': str(e)})
    return render(request, 'core/login.html')

def catalogo(request):
    productos = Producto.objects.filter(activo=True).order_by('nombre')
    categorias = Producto.objects.filter(activo=True).values_list('categoria', flat=True).distinct()
    if request.GET.get('categoria'):
        productos = productos.filter(categoria=request.GET.get('categoria'))
    if request.GET.get('precio_max'):
        productos = productos.filter(precio__lte=request.GET.get('precio_max'))
    context = {'productos': productos, 'categorias': categorias}
    return render(request, 'core/catalogo.html', context)

@login_required
def carrito(request):
    carrito = Carrito.objects.filter(
        usuario=request.user,
        creado__gte=timezone.now() - timezone.timedelta(minutes=15)
    ).first()
    if not carrito:
        return render(request, 'core/carrito.html', {'mensaje': 'Tu carrito está vacío'})
    items = carrito.itemcarrito_set.all()
    for item in items:
        item.subtotal = item.producto.precio * Decimal(item.cantidad)
    total = sum(item.subtotal for item in items)
    context = {
        'carrito': carrito,
        'items': items,
        'total': total,
    }
    return render(request, 'core/carrito.html', context)

@login_required
def mis_compras(request):
    ordenes = Orden.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'core/mis_compras.html', {'ordenes': ordenes})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def admin_panel(request):
    try:
        perfil = Perfil.objects.get(usuario=request.user)
        if not perfil.es_admin:
            return redirect('home')
    except Perfil.DoesNotExist:
        return redirect('home')
    productos = Producto.objects.all()
    ordenes = Orden.objects.all()
    return render(request, 'core/admin_panel.html', {'productos': productos, 'ordenes': ordenes})

@login_required
def add_to_carrito(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id, activo=True)
    carrito, created = Carrito.objects.get_or_create(
        usuario=request.user,
        creado__gte=timezone.now() - timezone.timedelta(minutes=15)
    )
    item, created = ItemCarrito.objects.get_or_create(carrito=carrito, producto=producto)
    if not created:
        item.cantidad += 1
    item.save()
    return redirect('catalogo')

@login_required
def remove_from_carrito(request, item_id):
    item = get_object_or_404(ItemCarrito, id=item_id, carrito__usuario=request.user)
    producto = item.producto
    producto.stock += item.cantidad
    producto.save()
    item.delete()
    return redirect('carrito')

@login_required
def checkout(request):
    carrito = Carrito.objects.filter(
        usuario=request.user,
        creado__gte=timezone.now() - timezone.timedelta(minutes=15)
    ).first()
    if not carrito:
        return render(request, 'core/carrito.html', {'mensaje': 'Tu carrito está vacío'})
    items = carrito.itemcarrito_set.all()
    for item in items:
        item.subtotal = item.producto.precio * Decimal(item.cantidad)
    total = sum(item.subtotal for item in items)
    context = {
        'carrito': carrito,
        'items': items,
        'total': total,
    }
    return render(request, 'core/checkout.html', context)

class ProductoListAPIView(APIView):
    def get(self, request):
        productos = Producto.objects.filter(activo=True).order_by('nombre')
        categoria = request.query_params.get('categoria')
        precio_max = request.query_params.get('precio_max')
        if categoria:
            productos = productos.filter(categoria=categoria)
        if precio_max:
            try:
                productos = productos.filter(precio__lte=float(precio_max))
            except ValueError:
                return Response({"error": "precio_max debe ser un número válido"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ProductoSerializer(productos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def admin_home(request):
    productos_bajo_stock = Producto.objects.filter(stock__lt=10)
    estado_filtro = request.GET.get('estado', '')  # Filtro por estado desde la URL
    ordenes_query = Orden.objects.filter(estado__in=['pendiente', 'confirmacion', 'preparacion'])
    if estado_filtro:
        ordenes_query = ordenes_query.filter(estado=estado_filtro)
    ordenes = ordenes_query.order_by('-fecha')
    paginator = Paginator(ordenes, 10)  # 10 órdenes por página
    page_number = request.GET.get('page')
    ordenes_paginated = paginator.get_page(page_number)

    item_id = request.GET.get('delete_item')
    orden_id = request.GET.get('delete_orden')
    if item_id:
        try:
            item = ItemOrden.objects.get(id=item_id)
            orden = item.orden
            producto = item.producto
            cantidad = item.cantidad
            item.delete()
            producto.stock += cantidad
            producto.save()
            orden.total -= item.cantidad * item.precio
            orden.save()
            messages.success(request, f'Ítem "{producto.nombre}" eliminado de la orden #{orden.id}. Stock restaurado.')
        except ItemOrden.DoesNotExist:
            messages.error(request, 'Ítem no encontrado.')
    elif orden_id:
        try:
            orden = Orden.objects.get(id=orden_id)
            orden.estado = 'cancelado'  # Esto activa el método save para restaurar stock
            orden.save()
            messages.success(request, f'Orden #{orden.id} cancelada y stock restaurado.')
        except Orden.DoesNotExist:
            messages.error(request, 'Orden no encontrada.')
            
    context = {
        'productos_bajo_stock': productos_bajo_stock,
        'ordenes': ordenes_paginated,
        'estado_filtro': estado_filtro,
    }
    return render(request, 'core/admin_home.html', context)

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def producto_list(request):
    productos = Producto.objects.all().order_by('nombre')
    return render(request, 'core/admin_productos.html', {'productos': productos})

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def producto_create(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto creado exitosamente.')
            return redirect('producto_list')
        else:
            messages.error(request, 'Error en el formulario. Revisa los campos.')
    else:
        form = ProductoForm()
    return render(request, 'core/producto_form.html', {'form': form, 'action': 'Crear'})

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def producto_update(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto actualizado exitosamente.')
            return redirect('producto_list')
        else:
            messages.error(request, 'Error en el formulario. Revisa los campos.')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'core/producto_form.html', {'form': form, 'action': 'Editar', 'producto': producto})

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def producto_delete(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, 'Producto eliminado exitosamente.')
        return redirect('producto_list')
    return render(request, 'core/producto_confirm_delete.html', {'producto': producto})

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def orden_detail(request, orden_id):
    orden = get_object_or_404(Orden, id=orden_id)
    items = orden.itemorden_set.all()
    return render(request, 'core/orden_detail.html', {'orden': orden, 'items': items})

def test_endpoint_view(request):
    response_data = None
    if request.method == 'POST':
        from django.test import Client
        try:
            client = Client()
            response = client.post(reverse('probar_orden'))
            if response.status_code == 201:
                response_data = response.json()
            else:
                response_data = {"error": "Fallo en la solicitud", "detalle": response.content.decode()}
        except Exception as e:
            response_data = {"error": str(e)}
    return render(request, 'core/test_endpoint.html', {'response': response_data})

# Nuevas vistas para los endpoints de API
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Carrito, ItemCarrito, Orden, ItemOrden, User, Producto
from .serializers import OrdenSerializer
from decimal import Decimal

class CrearOrdenView(APIView):
    def post(self, request):
        print("Datos recibidos:", request.data)
        try:
            usuario = request.user if request.user.is_authenticated else User.objects.get_or_create(username='testuser')[0]
        except User.DoesNotExist:
            usuario = User.objects.create(username='testuser')
            usuario.save()

        carrito = Carrito.objects.filter(
            usuario=usuario,
            creado__gte=timezone.now() - timezone.timedelta(minutes=15)
        ).order_by('-creado').first()
        if not carrito:
            print("No se encontró carrito válido")
            return Response({"error": "No se encontró un carrito válido"}, status=status.HTTP_400_BAD_REQUEST)

        items_carrito = ItemCarrito.objects.filter(carrito=carrito)
        if not items_carrito.exists():
            print("Carrito vacío")
            return Response({"error": "El carrito está vacío"}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        metodo_pago = data.get('metodo_pago', 'transferencia')
        total = Decimal(str(data.get('total', '0')))

        calculated_total = sum(item.cantidad * item.producto.precio for item in items_carrito)
        print(f"Calculated total: {calculated_total}, Received total: {total}")
        if abs(calculated_total - total) > Decimal('0.01'):
            print("Totales no coinciden")
            return Response({"error": "El total no coincide con los ítems"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            orden = Orden.objects.create(
                usuario=usuario,
                total=total,
                estado='confirmacion',
                metodo_pago=metodo_pago
            )
            for item in items_carrito:
                ItemOrden.objects.create(
                    orden=orden,
                    producto=item.producto,
                    cantidad=item.cantidad,
                    precio=item.producto.precio
                )
            items_carrito.delete()

        serializer = OrdenSerializer(orden)
        whatsapp_link = serializer.data['whatsapp_link']
        print(f"WhatsApp link: {whatsapp_link}")

        return Response({"whatsapp_link": whatsapp_link}, status=status.HTTP_200_OK)
    
@login_required
def checkout(request):
    carrito = Carrito.objects.filter(
        usuario=request.user,
        creado__gte=timezone.now() - timezone.timedelta(minutes=15)
    ).order_by('-creado').first()
    if not carrito:
        return render(request, 'core/carrito.html', {'mensaje': 'Tu carrito está vacío'})
    items = carrito.itemcarrito_set.all()
    for item in items:
        item.subtotal = item.producto.precio * Decimal(item.cantidad)
    total = sum(item.subtotal for item in items)
    context = {
        'carrito': carrito,
        'items': items,
        'total': total,
    }
    return render(request, 'core/checkout.html', context)

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Orden
from django.core.mail import send_mail
from django.conf import settings

def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def update_orden_status(request, orden_id):
    orden = get_object_or_404(Orden, id=orden_id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        comprobante = request.POST.get('comprobante', '')  # Obtener el valor del comprobante
        if nuevo_estado in dict(Orden.ESTADOS):
            orden.estado = nuevo_estado
            orden.comprobante = comprobante  # Guardar el comprobante
            orden.save()
            messages.success(request, f'El estado de la orden #{orden.id} se actualizó a {orden.get_estado_display()}.')
            if orden.usuario.email:
                subject = f'Actualización de tu orden #{orden.id}'
                message = f'Hola {orden.usuario.username},\nEl estado de tu orden #{orden.id} ha cambiado a {orden.get_estado_display()}.\nTotal: ${orden.total}\nMétodo de pago: {orden.get_metodo_pago_display()}\n{orden.instrucciones_transferencia}\nComprobante: {orden.comprobante or "No proporcionado"}'
                from_email = settings.EMAIL_HOST_USER
                to_email = orden.usuario.email
                send_mail(subject, message, from_email, [to_email], fail_silently=True)
        else:
            messages.error(request, 'Estado no válido.')
        return redirect('admin_panel')
    context = {
        'orden': orden,
        'instrucciones': orden.instrucciones_transferencia,
    }
    return render(request, 'core/update_orden_status.html', context)
# ===== MIS COMPRAS =====
@login_required
def mis_compras(request):
    """
    Lista las órdenes del usuario autenticado con filtros y datos preparados
    para la UI de seguimiento (tracker).
    """
    ordenes = (
        Orden.objects.filter(usuario=request.user)
        .select_related("usuario")
        .prefetch_related("itemorden_set__producto")
        .order_by("-fecha")
    )

    estado = request.GET.get("estado")
    if estado and estado in dict(Orden.ESTADOS):
        ordenes = ordenes.filter(estado=estado)

    q = request.GET.get("q")
    if q:
        if q.isdigit():
            ordenes = ordenes.filter(id=int(q))

    # Calcular subtotales en la vista
    for orden in ordenes:
        for item in orden.itemorden_set.all():
            item.subtotal = item.cantidad * item.precio

    ctx = {
        "ordenes": ordenes,
        "ESTADOS": Orden.ESTADOS,
    }
    return render(request, 'core/mis_compras.html', ctx)