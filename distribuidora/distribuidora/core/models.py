from django.db import models, transaction
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import datetime

class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    nombre_completo = models.CharField(max_length=100, validators=[RegexValidator(r'^[a-zA-Z\s]+$', 'Solo letras y espacios.')])
    rut = models.CharField(
        max_length=12, unique=True,
        validators=[RegexValidator(r'^\d{1,2}\.\d{3}\.\d{3}-[\dkK]$', 'Formato RUT invalido (ej: 12.345.678-9).')]
    )
    telefono = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"{self.nombre_completo} ({self.rut})"

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    categoria = models.CharField(max_length=50)
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    fecha_vencimiento = models.DateField(null=True, blank=True)
    imagen = models.ImageField(upload_to='productos/', blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    def clean(self):
        if self.stock < 0:
            raise ValidationError("Stock no puede ser negativo.")

    def bajo_stock(self):
        return self.stock < 10

class Carrito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.creado < timezone.now() - datetime.timedelta(minutes=15):
            for item in self.itemcarrito_set.all():
                item.producto.stock += item.cantidad
                item.producto.save()
            raise ValidationError("Carrito expirado.")

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.producto.stock < self.cantidad:
            raise ValidationError("Stock insuficiente.")
        self.producto.stock -= self.cantidad
        self.producto.save()
        super().save(*args, **kwargs)

class Orden(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente de Pago'),
        ('confirmacion', 'En Confirmacion'),
        ('preparacion', 'En Preparacion'),
        ('despacho', 'En Despacho/Listo para Retiro'),
        ('cancelado', 'Cancelado'),
    ]
    METODOS_PAGO = [
        ('transferencia', 'Transferencia Bancaria'),
        ('efectivo', 'Pago en Efectivo (Retiro)'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO, default='transferencia')
    instrucciones_transferencia = models.TextField(default="Realice transferencia a Cuenta XYZ y envie comprobante.")
    comprobante = models.TextField(blank=True, help_text="Nota o enlace a comprobante de transferencia (opcional).")

    def __str__(self):
        return f"Orden #{self.id} - {self.usuario.username}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.estado == 'cancelado':
            for item in self.itemorden_set.all():
                item.producto.stock += item.cantidad
                item.producto.save()

class ItemOrden(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

class ConfiguracionHome(models.Model):
    fotos_carrusel = models.JSONField(default=list)
    numero_contacto = models.CharField(max_length=15)
    ultima_actualizacion = models.DateTimeField(auto_now=True)