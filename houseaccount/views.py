from django.http import HttpResponse
from django.template import RequestContext, loader
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.shortcuts import redirect
from brothers.models import Brother, Payment, PaymentDue, HouseAccount
import datetime, traceback

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

  context = RequestContext(request, {'state':state, 'username':username})
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

  context = RequestContext(request, {'state':state,'datepurchased':date,
                                    'amount':amount,'description':desc})
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

  context = RequestContext(request, {'startdate':startdate,
                                    'brothers':Brother.objects.all()})
  return HttpResponse(template.render(context))

def submit_house_account(request):
  template = loader.get_template('submit-house-account.html')
  account = HouseAccount(date_created=datetime.date.today().strftime('%Y-%m-%d'))
  payments_due = _create_payments(request)

  account.save()
  for payment_due in payments_due:
    payment_due.houseaccount = account
    payment_due.save()

  context = RequestContext(request, {'payments_due':payments_due})
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

def _get_first_date():
  account = HouseAccount.first_house_account()
  payment = Payment.first_payment()
  if account:
    return account
  elif payment:
    return payment
  return datetime.date.today()

def _create_payments(request):
  proportions = _get_proportions(request)
  payments = Payment.get_payments_after(_get_first_date())
  if not payments:
    return []

  bros_owe = _get_amount_owed(payments, proportions)
  for payment in payments:
    bros_owe[payment.brother.name] -= float(payment.amount)
  payments_due = _distribute_payments(bros_owe)
  print(payments_due)
  return payments_due

def _get_proportions(request):
  proportions = {}
  if Brother.objects.all():
    for brother in Brother.objects.all():
      proportions[brother.name] = float(str(request.POST.get(brother.name)))
  return proportions

def _get_amount_owed(payments, proportions):
  bros_owe = {}
  for bro in Brother.objects.all():
    bros_owe[bro.name] = 0
  for payment in payments:
    bros_owe = _distribute_cost(payment.amount, bros_owe, '')
  for bro in bros_owe:
    bros_owe = _distribute_cost(float(bros_owe[bro]) * (1 - proportions[bro]), bros_owe, bro)
    bros_owe[bro] = bros_owe[bro] * proportions[bro]
  return bros_owe

def _distribute_cost(payment, bros_owe, except_bro):
  portion = payment / len(bros_owe)
  for bro in bros_owe:
    if bro != except_bro:
      bros_owe[bro] += float(portion)
  return bros_owe

def _distribute_payments(bros_owe):
  payments_due = []

  # First round: everyone pays the person owed the most
  bro_owed_most = sorted(bros_owe.items(), key=lambda x: x[1])[0][0]
  for bro in bros_owe:
    if bros_owe[bro] <= 0:
      continue
    paying_brother = Brother.objects.filter(name=bro)[0]
    payee_brother = Brother.objects.filter(name=bro_owed_most)[0]
    payments_due.append(PaymentDue(payer=paying_brother, payee=payee_brother,
                                   amount=round(bros_owe[bro], 2)))
    bros_owe[bro_owed_most] += bros_owe[bro]
    bros_owe[bro] = 0

  # Second round: person paid now pays everyone who still needs payment
  for bro in bros_owe:
    if bros_owe[bro] >= 0:
      continue
    paying_brother = Brother.objects.filter(name=bro_owed_most)[0]
    payee_brother = Brother.objects.filter(name=bro)[0]
    payments_due.append(PaymentDue(payer=paying_brother, payee=payee_brother,
                                   amount=round(bros_owe[bro], 2)))
    bros_owe[bro_owed_most] += bros_owe[bro]
    bros_owe[bro] = 0
  _round_amounts(bros_owe)

  return payments_due

def _round_amounts(bros_owe):
  for bro in bros_owe:
    bros_owe[bro] = round(bros_owe[bro], 2)
