from django.http import HttpResponse
from django.template import RequestContext, loader
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.shortcuts import redirect
from brothers.models import Brother, Payment, PaymentDue, HouseAccount
import datetime

# Request handlers

def login_user(request):
  template = loader.get_template('auth.html')
  state = ''
  success = True
  username = password = ''

  if not request.POST and request.user.is_authenticated():
    return redirect('/welcome')

  if request.POST:
    username = request.POST.get('username')
    password = request.POST.get('password')

    if 'login' in request.POST:
      user = authenticate(username=username, password=password)
      if user is not None:
        if user.is_active:
          login(request, user)
          state = 'You have logged in'
        else:
          success = False
          state = 'You have an inactive account and cannot be logged in'
      else:
        success = False
        state = 'Incorrect username and password combination'

    elif 'join' in request.POST:
      if User.objects.filter(username=username).count():
        success = False
        state = 'A user with this name is already registered'
      else:
        success = False
        if password:
          user = User.objects.create_user(username, '', password)
          user.save()
          brother = Brother(user=user, name=username, created_date=timezone.now())
          brother.save()
          state = 'Congratulations! Your account has been registered'
        else:
          state = 'Please enter a valid password'

  if success and request.user.is_authenticated():
    return redirect('/welcome')

  context = RequestContext(request, {'state':state, 'username':username, 'success':success})
  return HttpResponse(template.render(context))

def enter_payment(request):
  template = loader.get_template('payment.html')
  state = ''
  success = True
  date = amount = desc = ''

  if request.POST:
    date = request.POST.get('datepurchased')
    amount = request.POST.get('amount')
    desc = request.POST.get('description')

    date_purchased, state = _validate_date(date)
    amt, temp = _validate_amount(amount)
    if temp and not state:
      state = temp
    if date_purchased is None or amt is None:
      success = False

  if request.POST and success:
    state = 'Congratulations! You entered a payment of ' + amount + \
            '. Place your receipt in Ruiyu\'s folder'
    brother = Brother.objects.filter(user=request.user)[0]
    payment = Payment(brother=brother,amount=amt,description=desc,
                      date_purchased=date_purchased,date_entered=timezone.now())
    payment.save()

  context = RequestContext(request, {'state':state,'success':success,
                                    'datepurchased':date,'amount':amount,'description':desc})
  return HttpResponse(template.render(context))

def logout_user(request):
  logout(request)
  return redirect('/login')

def landing_page(request):
  template = loader.get_template('landing.html')
  context = RequestContext(request, {})
  return HttpResponse(template.render(context))

def create_house_account(request):
  template = loader.get_template('create-house-account.html')
  startdate = _get_first_date().strftime('%B %d, %Y')

  context = RequestContext(request, {'startdate':startdate if startdate else enddate,
                                    'brothers':Brother.objects.all()})
  return HttpResponse(template.render(context))

def submit_house_account(request):
  """
  template = loader.get_template('submit-house-account.html')
  payments = Payment.objects.filter(date_entered__gte=_get_first_date())
  proportions = _get_proportions(request)
  payments_due = _calculate_average_payment(payments, proportions)
  context = RequestContext(request, {'state':'','payments_due':payments})
  return HttpResponse(template.render(context))
  """
  template = loader.get_template('submit-house-account.html')
  state = ''
  proportions = amount_due_per_brother = {}
  payments = payments_due = []
  success = True

  if not request.POST:
    return HttpResponse('No form values were entered.')
  else:
    try:
      proportions = _get_proportions(request)
    except Exception as e:
      state = 'Invalid proportion input'
    try:
      payments = Payment.objects.filter(date_entered__gt=_get_first_date())
      payments_due, amount_due_per_brother, account = \
                _generate_payments(payments, proportions)
    except Exception as e:
      state = e

  for bro in amount_due_per_brother:
    if amount_due_per_brother[bro] != 0:
      success = False
  if success and payments_due:
    for payment_due in payments_due:
      payment_due.save()
  else:
    account.delete()

  context = RequestContext(request, {'state':state,'payments_due':payments_due,
                                    'success':success})
  return HttpResponse(template.render(context))

# Private methods

def _validate_date(date):
  message = 'Please enter a valid date'
  ymd = date.split('/')
  if len(ymd) != 3:
    return (None, message)
  try:
    ret = datetime.date(int(ymd[0]), int(ymd[1]), int(ymd[2]))
  except:
    return (None, message)
  return (ret, '')

def _validate_amount(amount):
  message = 'Please enter a valid payment amount'
  try:
    amt = float(amount)
  except:
    return (None, message)
  return (amt, '')

def _get_proportions(request):
  proportions = {}
  if Brother.objects.all():
    for brother in Brother.objects.all():
      proportions[brother.name] = float(str(request.POST.get(brother.name)))
  return proportions

def _get_first_date():
  accounts = HouseAccount.objects.order_by('date_created')
  payments = Payment.objects.order_by('date_entered')
  if accounts:
    return accounts[0].date_created
  elif payments:
    return payments[0].date_entered
  else:
    return timezone.now()

def _get_bro_with_least_due(amount_due_per_brother):
  bro_with_least_due = None
  minimum = 0
  for brother in amount_due_per_brother:
    if bro_with_least_due == None or amount_due_per_brother[brother] < minimum:
      bro_with_least_due = brother
      minimum = amount_due_per_brother[brother]
  return bro_with_least_due

def _calculate_average_payment(payments, proportions):
  total_spent = sum([payment.amount for payment in payments])
  return float(total_spent / len(proportions))

def _generate_payments(payments, proportions):
  houseaccount = HouseAccount(date_created=timezone.now())
  houseaccount.save()
  payments_due = bros_due_payment = []
  total_spent = sum([payment.amount for payment in payments])
  total_divided_equally = 0
  amount_due_per_brother = {}

  for brother in proportions:
    total_divided_equally = proportions[brother] * float(total_spent) / len(proportions)
    amount_due_per_brother[brother] = total_divided_equally
    amt = [payment.amount for payment in payments if payment.brother.name == brother]
    amount_due_per_brother[brother] -= float(sum(amt))
    amount_due_per_brother[brother] = round(amount_due_per_brother[brother], 2)
  
  bro_with_least_due = _get_bro_with_least_due(amount_due_per_brother)
  brother_with_least_due = Brother.objects.filter(name=bro_with_least_due)[0]

  # By now, we have how much everyone is owed and how much everyone owes, and
  # those who owe the account pay the one with the least due
  for brother in amount_due_per_brother:
    payer = Brother.objects.filter(name=brother)[0]
    if amount_due_per_brother[brother] > 0:
      payment_due = PaymentDue(payer=payer,payee=brother_with_least_due,
                              houseaccount=houseaccount,
                              amount=amount_due_per_brother[brother])
      payments_due += [payment_due]
      amount_due_per_brother[bro_with_least_due] += amount_due_per_brother[brother]
      amount_due_per_brother[brother] -= amount_due_per_brother[brother]
  
  # Now, each person who owed money has paid the person who was owed the most.
  # Recursively, he should pay the person owed next most his excess, 
  # and that person the next most, and so on. Yay, recursion!
  def pay_next_person(amount_due_per_brother, payments_due, houseaccount):
    bro_with_least_due = _get_bro_with_least_due(amount_due_per_brother)
    brother_with_least_due = Brother.objects.filter(name=bro_with_least_due)[0]
    if amount_due_per_brother[bro_with_least_due] < 0:
      for brother in amount_due_per_brother:
        payer = Brother.objects.filter(name=brother)[0]
        if amount_due_per_brother[brother] > 0:
          payment_due = PaymentDue(payer=payer,payee=brother_with_least_due,
                                  houseaccount=houseaccount,
                                  amount=amount_due_per_brother[brother])
          payments_due += [payment_due]
          amount_due_per_brother[bro_with_least_due] += amount_due_per_brother[brother]
          amount_due_per_brother[brother] -= amount_due_per_brother[brother]
    return (payments_due, amount_due_per_brother, houseaccount)

  return pay_next_person(amount_due_per_brother, payments_due, houseaccount)
