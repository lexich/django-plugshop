# encoding: utf-8
import datetime
from django.db import models
from django.utils.translation import ugettext_lazy as _

from plugshop.models import ProductAbstract, CategoryAbstract, OrderAbstract

class Product(ProductAbstract):
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(blank=True, null=True, 
                                      default=datetime.datetime.now)
    sort = models.PositiveIntegerField(blank=True, null=True, default=1)

class Category(CategoryAbstract):
    description = models.TextField(blank=True)
    
class Order(OrderAbstract):
    city = models.CharField(_('city'), max_length=80)
    address = models.TextField(_('address'), )
    zip_code = models.CharField(_('zip'), max_length=24)
    phone = models.CharField(_('phone'), max_length=80)