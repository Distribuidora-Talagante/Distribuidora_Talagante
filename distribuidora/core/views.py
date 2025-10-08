from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Producto

def home(request):
    return render(request, 'core/home.html', {'mensaje': 'Bienvenido a Distribuidora Talagante'})

def catalogo(request):
    productos = Producto.objects.filter(activo=True).order_by('nombre')  
    if request.GET.get('categoria'):
        productos = productos.filter(categoria=request.GET.get('categoria'))
    if request.GET.get('precio_max'):
        productos = productos.filter(precio__lte=request.GET.get('precio_max'))
    context = {'productos': productos}
    return render(request, 'core/catalogo.html', context)
    
def carrito(request):
    return render(request, 'core/carrito.html', {'mensaje': 'Tu carrito está vacío'})

@login_required
def mis_compras(request):
    from .models import Orden
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
    from .models import Producto, Orden
    productos = Producto.objects.all()
    ordenes = Orden.objects.all()
    return render(request, 'core/admin_panel.html', {'productos': productos, 'ordenes': ordenes})

@login_required
def add_to_carrito(request, producto_id):
    producto = Producto.objects.get(id=producto_id)
    carrito, created = Carrito.objects.get_or_create(usuario=request.user, creado__gte=timezone.now() - datetime.timedelta(minutes=15))
    item, created = ItemCarrito.objects.get_or_create(carrito=carrito, producto=producto)
    if not created:
        item.cantidad += 1
    item.save()
    return redirect(reverse('catalogo'))