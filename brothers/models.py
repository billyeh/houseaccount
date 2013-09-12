from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Brother(models.Model):
  user = models.ForeignKey(User, unique=True)
  name = models.CharField(max_length=100)
  created_date = models.DateTimeField('date created')

  def __unicode__(self):
    return self.name

class HouseAccount(models.Model):
  date_created = models.DateTimeField('date created')

  def __unicode__(self):
    return str(self.date_created if self.date_created else 'No date') + ' house account'

class Payment(models.Model):
  brother = models.ForeignKey(Brother)
  amount = models.DecimalField(max_digits=10, decimal_places=2)
  description = models.CharField(max_length=160)
  date_purchased = models.DateTimeField('date purchased')
  date_entered = models.DateTimeField('date entered')

  def __unicode__(self):
    return '$' + str(self.amount) + ' by ' + str(self.brother) + ' on ' + \
           self.date_purchased.strftime('%B %d, %Y')

class PaymentDue(models.Model):
  payer = models.ForeignKey(Brother, related_name='payment_due_payer')
  payee = models.ForeignKey(Brother, related_name='payment_due_payee')
  houseaccount = models.ForeignKey(HouseAccount)
  amount = models.DecimalField(max_digits=10, decimal_places=2)

  def __unicode__(self):
    return str(self.payer) + ' pays ' + str(self.payee) + ' ' + str(self.amount)