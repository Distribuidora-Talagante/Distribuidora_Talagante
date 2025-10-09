from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response 
from rest_framework import status
from .models import Producto, Orden, Carrito, ItemCarrito
from .serializers import ProductoSerializer
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.shortcuts import render, redirect
from core.models import Perfil
from decimal import Decimal

def home(request):
    return render(request, 'core/home.html', {'mensaje': 'Bienvenido a Distribuidora Talagante'})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
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

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        nombre_completo = request.POST['nombre_completo']
        rut = request.POST['rut']
        telefono = request.POST.get('telefono', '')
        # Validate username and RUT uniqueness
        if User.objects.filter(username=username).exists():
            return render(request, 'core/login.html', {'reg_error': 'El usuario ya existe'})
        if Perfil.objects.filter(rut=rut).exists():
            return render(request, 'core/login.html', {'reg_error': 'El RUT ya está registrado'})
        # Create user and profile
        try:
            user = User.objects.create_user(username=username, password=password)
            perfil = Perfil.objects.create(
                usuario=user,
                nombre_completo=nombre_completo,
                rut=rut,
                telefono=telefono,
                es_admin=False  # Default to Client
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

def carrito(request):
    return render(request, 'core/carrito.html', {'mensaje': 'Tu carrito está vacío'})

@login_required
def mis_compras(request):
    ordenes = Orden.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'core/mis_compras.html', {'ordenes': ordenes})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'core/login.html', {'error': 'Credenciales inválidas'})
    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def admin_panel(request):
    if not request.user.is_admin:
        return redirect('home')
    productos = Producto.objects.all()
    ordenes = Orden.objects.all()
    return render(request, 'core/admin_panel.html', {'productos': productos, 'ordenes': ordenes})

@login_required
def carrito(request):
    # Obtener el carrito activo del usuario (creado en los últimos 15 minutos)
    carrito = Carrito.objects.filter(
        usuario=request.user,
        creado__gte=timezone.now() - timezone.timedelta(minutes=15)
    ).first()
    if not carrito:
        return render(request, 'core/carrito.html', {'mensaje': 'Tu carrito está vacío'})
    # Calcular subtotales y total
    items = carrito.itemcarrito_set.all()
    for item in items:
        item.subtotal = item.producto.precio * Decimal(item.cantidad)  # Usar Decimal en lugar de decimal.Decimal
    total = sum(item.subtotal for item in items)  # Total general
    context = {
        'carrito': carrito,
        'items': items,
        'total': total,
    }
    return render(request, 'core/carrito.html', context)

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
    item.save()  # Esto activa la lógica de stock en models.py
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
    # Obtener el carrito activo del usuario (creado en los últimos 15 minutos)
    carrito = Carrito.objects.filter(
        usuario=request.user,
        creado__gte=timezone.now() - timezone.timedelta(minutes=15)
    ).first()
    if not carrito:
        return render(request, 'core/carrito.html', {'mensaje': 'Tu carrito está vacío'})
    
    # Calcular subtotales y total
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